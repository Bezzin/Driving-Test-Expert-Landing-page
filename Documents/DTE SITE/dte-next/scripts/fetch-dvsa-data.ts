import * as XLSX from 'xlsx'
import * as fs from 'fs'
import * as path from 'path'
import type { DvsaCentre } from '../lib/dvsa-types'

const DATA_DIR = path.resolve(__dirname, '..', 'data', 'dvsa')

const ODS_URLS: Record<string, string> = {
  drt122a:
    'https://assets.publishing.service.gov.uk/media/689c5ec6d2a1b0d5d1bb1251/drt122a-car-driving-test-by-test-centre.ods',
  drt122b:
    'https://assets.publishing.service.gov.uk/media/689c5ed187bf475940723ee1/drt122b-car-driving-test-cancellations-by-test-centre.ods',
  drt122c:
    'https://assets.publishing.service.gov.uk/media/689c5c9b1c63de6de5bb1249/drt122c-car-driving-test-first-attempt-by-test-centre.ods',
  drt122d:
    'https://assets.publishing.service.gov.uk/media/689c5cad87bf475940723edd/drt122d-car-driving-test-by-age-by-test-centre.ods',
  drt122e:
    'https://assets.publishing.service.gov.uk/media/689c59491c63de6de5bb1246/drt122e-car-driving-test-automatic-by-test-centre.ods',
}

// ── Helpers ──────────────────────────────────────────────────────

function toSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/\(([^)]+)\)/g, '$1') // remove parens, keep contents
    .replace(/[^a-z0-9]+/g, '-') // non-alphanum → hyphen
    .replace(/^-+|-+$/g, '') // trim leading/trailing hyphens
}

function normaliseName(raw: string): string {
  return raw.trim().replace(/\s+/g, ' ')
}

function parseNumeric(val: unknown): number | null {
  if (val === null || val === undefined || val === '') return null
  const s = String(val).trim()
  if (s === '..' || s === 'x' || s === 'c' || s === '-' || s === 'N/A') return null
  const n = Number(s)
  return isNaN(n) ? null : n
}

function normaliseRate(val: unknown): number | null {
  const n = parseNumeric(val)
  if (n === null) return null
  // DVSA pass rates are already in percentage form (e.g. 45.2, not 0.452)
  // But double-check: if < 1 it's probably a decimal
  if (n >= 0 && n <= 1) return Math.round(n * 1000) / 10
  return Math.round(n * 10) / 10
}

function isCentreName(val: unknown): boolean {
  const s = String(val ?? '').trim()
  if (!s || s.length < 3) return false
  // Skip date-like values, numeric serial dates, month names, headers, national totals
  if (/^\d+$/.test(s)) return false
  if (/^\d{4}/.test(s)) return false
  if (/^(January|February|March|April|May|June|July|August|September|October|November|December)\b/i.test(s)) return false
  if (/^(Apr-|Jan-|Jul-|Oct-)/i.test(s)) return false
  if (/^NATIONAL/i.test(s)) return false
  if (/^National$/i.test(s)) return false
  if (/^(Note|Please|Time|DRT|Conducted|Passes|Pass rate|Male|Female|Total|Leave|Disputes|Acts|Medical|Pandemic|Age|Cancellation|Numbers)/i.test(s)) return false
  if (s === '' || s === ' ') return false
  // Must start with a letter
  if (!/^[A-Za-z]/.test(s)) return false
  return true
}

function isCentreNameNotClosed(val: unknown): boolean {
  if (!isCentreName(val)) return false
  const s = String(val).trim()
  // Skip closed centres (prefixed with Z)
  if (/^Z[A-Z]/.test(s)) return false
  return true
}

async function downloadFile(url: string, filename: string): Promise<Buffer> {
  const filePath = path.join(DATA_DIR, filename)
  if (fs.existsSync(filePath)) {
    console.log(`  Using cached: ${filename}`)
    return fs.readFileSync(filePath)
  }
  console.log(`  Downloading: ${filename}...`)
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to download ${url}: ${response.status}`)
  }
  const buffer = Buffer.from(await response.arrayBuffer())
  fs.writeFileSync(filePath, buffer)
  return buffer
}

function loadSheet(workbook: XLSX.WorkBook, sheetName: string): unknown[][] {
  const sheet = workbook.Sheets[sheetName]
  if (!sheet) throw new Error(`Sheet "${sheetName}" not found`)
  return XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' }) as unknown[][]
}

// ── DRT122A: Pass rates by gender (primary dataset) ─────────────

interface A_CentreData {
  name: string
  testsConductedMale: number
  testsConductedFemale: number
  testsConductedTotal: number
  passRateMale: number
  passRateFemale: number
  passRateOverall: number
}

function parseA_Sheet(workbook: XLSX.WorkBook, sheetName: string): Map<string, A_CentreData> {
  const rows = loadSheet(workbook, sheetName)
  const centres = new Map<string, A_CentreData>()

  // The structure: centre name header row (just name in col 0, rest empty),
  // followed by monthly rows, then a summary row with the centre name repeated
  // and aggregate data. We want the summary rows.
  for (let i = 6; i < rows.length; i++) {
    const row = rows[i]
    const firstCell = String(row[0] ?? '').trim()

    if (!isCentreNameNotClosed(firstCell)) continue

    // Check if this row has numeric data (summary row) vs being a header row
    const conductedTotal = parseNumeric(row[9])
    const passRateTotal = normaliseRate(row[11])

    if (conductedTotal !== null && conductedTotal > 0 && passRateTotal !== null) {
      const name = normaliseName(firstCell)
      const conductedMale = parseNumeric(row[1]) ?? 0
      const passesMale = parseNumeric(row[2])
      const passRateMale = normaliseRate(row[3])
      const conductedFemale = parseNumeric(row[5]) ?? 0
      const passRateFemale = normaliseRate(row[7])

      centres.set(name, {
        name,
        testsConductedMale: conductedMale,
        testsConductedFemale: conductedFemale,
        testsConductedTotal: conductedTotal,
        passRateMale: passRateMale ?? 0,
        passRateFemale: passRateFemale ?? 0,
        passRateOverall: passRateTotal,
      })
    }
  }

  return centres
}

function extractHistoricalRates(
  workbook: XLSX.WorkBook,
  yearsToExtract: string[]
): Map<string, Array<{ year: string; rate: number }>> {
  const history = new Map<string, Array<{ year: string; rate: number }>>()

  for (const year of yearsToExtract) {
    if (!workbook.SheetNames.includes(year)) continue
    const centres = parseA_Sheet(workbook, year)
    const yearLabel = year.replace('-', '/')

    for (const [name, data] of centres) {
      const existing = history.get(name) ?? []
      existing.push({ year: yearLabel, rate: data.passRateOverall })
      history.set(name, existing)
    }
  }

  // Sort each centre's history chronologically
  for (const [name, arr] of history) {
    arr.sort((a, b) => a.year.localeCompare(b.year))
    history.set(name, arr)
  }

  return history
}

// ── DRT122B: Cancellations ───────────────────────────────────────

interface B_CentreData {
  dvsaCancelled: number
  candidateCancelled: number
  noShows: number
}

function parseB_Sheet(workbook: XLSX.WorkBook, sheetName: string): Map<string, B_CentreData> {
  const rows = loadSheet(workbook, sheetName)
  const centres = new Map<string, B_CentreData>()

  // Structure: centre name header, monthly rows, then summary row with centre name + totals
  // Columns: [name, Leave, Disputes, Acts of Nature, Medical Absences, (Pandemic?), Total]
  for (let i = 7; i < rows.length; i++) {
    const row = rows[i]
    const firstCell = String(row[0] ?? '').trim()

    if (!isCentreNameNotClosed(firstCell)) continue

    // Summary row has numeric data
    const totalCancelled = parseNumeric(row[row.length > 6 ? 6 : 5])
    if (totalCancelled === null || totalCancelled <= 0) continue

    // Only take summary rows (not monthly detail rows)
    // Summary rows have the centre name, monthly rows have month names
    const leave = parseNumeric(row[1]) ?? 0
    const disputes = parseNumeric(row[2]) ?? 0
    const actsOfNature = parseNumeric(row[3]) ?? 0
    const medical = parseNumeric(row[4]) ?? 0

    const name = normaliseName(firstCell)
    // DVSA cancelled = Leave + Disputes + Acts of Nature + Medical
    // These are all DVSA-side cancellations, not candidate cancellations
    // The DRT122B dataset only has DVSA cancellations, not candidate/no-show data
    centres.set(name, {
      dvsaCancelled: leave + disputes + actsOfNature + medical,
      candidateCancelled: 0,
      noShows: 0,
    })
  }

  return centres
}

// ── DRT122C: First-attempt pass rates ────────────────────────────

interface C_CentreData {
  passRateFirstAttempt: number | null
  passRateFirstAttemptMale: number | null
  passRateFirstAttemptFemale: number | null
  zeroFaultPasses: number | null
}

function parseC_Sheet(workbook: XLSX.WorkBook, sheetName: string): Map<string, C_CentreData> {
  const rows = loadSheet(workbook, sheetName)
  const centres = new Map<string, C_CentreData>()

  // DRT122C 2024-25 sheet: one row per centre (no monthly breakdown)
  // Row structure (15 cols):
  // [0] Name
  // [1] Male 1st attempts, [2] Male 1st passes, [3] Male pass%, [4] Male zero faults
  // [5] (empty)
  // [6] Female 1st attempts, [7] Female 1st passes, [8] Female pass%, [9] Female zero faults
  // [10] (empty)
  // [11] Total 1st attempts, [12] Total 1st passes, [13] Total pass%, [14] Total zero faults

  for (let i = 6; i < rows.length; i++) {
    const row = rows[i]
    const firstCell = String(row[0] ?? '').trim()

    if (!isCentreNameNotClosed(firstCell)) continue

    const totalFirstAttempts = parseNumeric(row[11])
    if (totalFirstAttempts === null || totalFirstAttempts <= 0) continue

    const name = normaliseName(firstCell)
    centres.set(name, {
      passRateFirstAttempt: normaliseRate(row[13]),
      passRateFirstAttemptMale: normaliseRate(row[3]),
      passRateFirstAttemptFemale: normaliseRate(row[8]),
      zeroFaultPasses: parseNumeric(row[14]),
    })
  }

  return centres
}

// ── DRT122D: Pass rates by age ───────────────────────────────────

function parseD_Sheet(workbook: XLSX.WorkBook, sheetName: string): Map<string, Record<string, number>> {
  const rows = loadSheet(workbook, sheetName)
  const centres = new Map<string, Record<string, number>>()

  // Structure: Centre name as header row, then age rows (17,18,...25,Total)
  // Columns: [0] (empty or name), [1] Age, [2-4] Male, [5-7] Female, [8-10] Total
  // We want ages 17-25 pass rates from the Total columns

  let currentCentre: string | null = null
  let currentAgeRates: Record<string, number> = {}

  for (let i = 7; i < rows.length; i++) {
    const row = rows[i]
    const firstCell = String(row[0] ?? '').trim()
    const secondCell = String(row[1] ?? '').trim()

    // Centre header row
    if (isCentreNameNotClosed(firstCell) && secondCell === '') {
      // Save previous centre
      if (currentCentre && Object.keys(currentAgeRates).length > 0) {
        centres.set(currentCentre, { ...currentAgeRates })
      }
      currentCentre = normaliseName(firstCell)
      currentAgeRates = {}
      continue
    }

    // Age data row
    if (currentCentre && secondCell) {
      const age = String(secondCell).trim()
      if (age === 'Total') {
        // Save and reset
        if (Object.keys(currentAgeRates).length > 0) {
          centres.set(currentCentre, { ...currentAgeRates })
        }
        currentCentre = null
        currentAgeRates = {}
        continue
      }

      const ageNum = parseInt(age, 10)
      if (!isNaN(ageNum) && ageNum >= 17 && ageNum <= 25) {
        const passRate = normaliseRate(row[10])
        if (passRate !== null) {
          currentAgeRates[String(ageNum)] = passRate
        }
      }
    }
  }

  // Don't forget the last centre
  if (currentCentre && Object.keys(currentAgeRates).length > 0) {
    centres.set(currentCentre, { ...currentAgeRates })
  }

  return centres
}

// ── DRT122E: Automatic car pass rates ────────────────────────────

function parseE_Sheet(workbook: XLSX.WorkBook, sheetName: string): Map<string, number> {
  const rows = loadSheet(workbook, sheetName)
  const centres = new Map<string, number>()

  // One row per centre, same layout as DRT122A but for automatic tests
  // [0] Name, [1-3] Male (Conducted/Passes/Rate), [4] empty, [5-7] Female, [8] empty, [9-11] Total
  for (let i = 7; i < rows.length; i++) {
    const row = rows[i]
    const firstCell = String(row[0] ?? '').trim()

    if (!isCentreNameNotClosed(firstCell)) continue

    const conducted = parseNumeric(row[9])
    if (conducted === null || conducted <= 0) continue

    const passRate = normaliseRate(row[11])
    if (passRate !== null) {
      centres.set(normaliseName(firstCell), passRate)
    }
  }

  return centres
}

// ── Region detection ─────────────────────────────────────────────

function detectRegion(name: string): string {
  const lower = name.toLowerCase()

  // Scotland
  const scotlandPatterns = [
    'aberdeen', 'dundee', 'edinburgh', 'glasgow', 'inverness', 'perth',
    'stirling', 'ayr', 'airdrie', 'arbroath', 'ballachulish', 'banff',
    'bathgate', 'buckie', 'campbeltown', 'castle douglas', 'cumnock',
    'cupar', 'dumbarton', 'dumfries', 'dunfermline', 'dunoon', 'elgin',
    'falkirk', 'forfar', 'fort william', 'fraserburgh', 'galashiels',
    'grangemouth', 'greenock', 'haddington', 'hamilton', 'hawick',
    'helensburgh', 'inveraray', 'irvine', 'jedburgh', 'kelso',
    'kilmarnock', 'kirkcaldy', 'kirkwall', 'lanark', 'lerwick',
    'livingston', 'lochgilphead', 'montrose', 'motherwell', 'musselburgh',
    'oban', 'paisley', 'peebles', 'pitlochry', 'portree', 'stornoway',
    'stranraer', 'thurso', 'wick', 'aberfeldy', 'coatbridge', 'cumbernauld',
    'east kilbride', 'kirkliston', 'anniesland',
    'alness', 'ballater', 'bishopbriggs', 'callander', 'crieff',
    'duns', 'gairloch', 'girvan', 'golspie', 'grantown',
    'huntly', 'inverurie', 'isle of mull', 'isle of tiree',
    'kingussie', 'kyle of lochalsh', 'mallaig', 'newton stewart',
    'orkney', 'peterhead', 'ullapool', 'benbecula', 'barra',
  ]
  if (scotlandPatterns.some((p) => lower.includes(p))) return 'Scotland'

  // Wales
  const walesPatterns = [
    'cardiff', 'swansea', 'newport', 'wrexham', 'aberystwyth', 'abergavenny',
    'bangor', 'bridgend', 'brecon', 'caernarfon', 'carmarthen', 'colwyn',
    'dolgellau', 'haverfordwest', 'llandrindod', 'llanelli', 'merthyr',
    'neath', 'pontypridd', 'rhyl', 'pembroke', 'pwllheli', 'welshpool',
    'barry', 'machynlleth', 'newtown', 'lampeter', 'llangefni',
    'bala', 'cardigan', 'llantrisant', 'monmouth',
  ]
  if (walesPatterns.some((p) => lower.includes(p))) return 'Wales'

  // Northern Ireland
  const niPatterns = [
    'belfast', 'ballymena', 'coleraine', 'cookstown', 'craigavon',
    'downpatrick', 'enniskillen', 'larne', 'lisburn', 'londonderry',
    'magherafelt', 'newry', 'newtownards', 'omagh', 'derry',
    'armagh', 'antrim', 'dungannon', 'limavady', 'strabane',
  ]
  if (niPatterns.some((p) => lower.includes(p))) return 'Northern Ireland'

  // London
  const londonPatterns = [
    'london', 'barking', 'barnet', 'bexleyheath', 'borehamwood',
    'bromley', 'cheetham', 'chingford', 'croydon', 'enfield',
    'erith', 'greenford', 'goodmayes', 'herne hill', 'hither green',
    'hornchurch', 'isleworth', 'mill hill', 'mitcham', 'morden',
    'pinner', 'sidcup', 'southall', 'south norwood', 'tolworth',
    'tottenham', 'uxbridge', 'wanstead', 'wembley', 'hendon',
    'wood green', 'wimbledon', 'belvedere', 'catford',
  ]
  if (londonPatterns.some((p) => lower.includes(p))) return 'London'

  // South East
  const sePatterns = [
    'brighton', 'canterbury', 'chichester', 'crawley', 'eastbourne',
    'gillingham', 'guildford', 'hastings', 'horsham', 'maidstone',
    'oxford', 'portsmouth', 'reading', 'slough', 'southampton',
    'tunbridge', 'worthing', 'ashford', 'aylesbury', 'basingstoke',
    'bognor', 'bracknell', 'chatham', 'colchester', 'farnborough',
    'folkestone', 'high wycombe', 'isle of wight', 'lewes', 'luton',
    'margate', 'newbury', 'reigate', 'sevenoaks', 'sittingbourne',
    'stevenage', 'watford', 'windsor', 'woking', 'hove',
    'basildon', 'bishops stortford', 'bletchley', 'burgess hill',
    'clacton', 'greenham', 'herne bay', 'lee on the solent',
    'leighton buzzard', 'letchworth', 'redhill',
    'bishops stortford', 'culham',
  ]
  if (sePatterns.some((p) => lower.includes(p))) return 'South East'

  // South West
  const swPatterns = [
    'bath', 'bournemouth', 'bristol', 'cheltenham', 'dorchester',
    'exeter', 'gloucester', 'plymouth', 'salisbury', 'swindon',
    'taunton', 'torquay', 'truro', 'yeovil', 'barnstaple', 'bodmin',
    'bridgwater', 'chippenham', 'cirencester', 'dorset', 'falmouth',
    'hereford', 'isle of scilly', 'isles of scilly', 'newquay', 'penzance', 'poole',
    'redruth', 'stroud', 'trowbridge', 'weston-super-mare', 'weymouth',
    'camborne', 'launceston', 'newton abbot',
  ]
  if (swPatterns.some((p) => lower.includes(p))) return 'South West'

  // East of England
  const eePatterns = [
    'bedford', 'cambridge', 'chelmsford', 'colchester', 'ipswich',
    'norwich', 'peterborough', 'southend', 'bury st edmunds',
    'great yarmouth', 'harlow', 'hertford', 'kings lynn',
    'lowestoft', 'st albans', 'hemel hempstead',
  ]
  if (eePatterns.some((p) => lower.includes(p))) return 'East of England'

  // West Midlands
  const wmPatterns = [
    'birmingham', 'coventry', 'dudley', 'halesowen', 'kidderminster',
    'nuneaton', 'redditch', 'shrewsbury', 'solihull', 'stafford',
    'stoke', 'sutton coldfield', 'tamworth', 'telford', 'walsall',
    'wednesbury', 'wolverhampton', 'worcester', 'cannock', 'oswestry',
    'wednesfield', 'oldbury', 'erdington', 'leamington', 'warwick',
    'lichfield', 'burton on trent', 'ludlow', 'upton',
  ]
  if (wmPatterns.some((p) => lower.includes(p))) return 'West Midlands'

  // East Midlands
  const emPatterns = [
    'derby', 'leicester', 'lincoln', 'nottingham', 'northampton',
    'boston', 'chesterfield', 'corby', 'grantham', 'kettering',
    'loughborough', 'mansfield', 'melton', 'skegness', 'wellingborough',
    'worksop', 'hinckley', 'market harborough', 'buxton',
    'ashfield', 'louth', 'watnall', 'rugby',
  ]
  if (emPatterns.some((p) => lower.includes(p))) return 'East Midlands'

  // Yorkshire and the Humber
  const yhPatterns = [
    'bradford', 'doncaster', 'halifax', 'huddersfield', 'hull',
    'leeds', 'rotherham', 'scarborough', 'sheffield', 'wakefield',
    'york', 'barnsley', 'beverley', 'bridlington', 'dewsbury',
    'goole', 'grimsby', 'harrogate', 'malton', 'selby',
    'scunthorpe', 'skipton', 'thirsk',
    'featherstone', 'heckmondwike', 'horsforth', 'knaresborough',
    'pontefract', 'steeton', 'northallerton', 'whitby',
  ]
  if (yhPatterns.some((p) => lower.includes(p))) return 'Yorkshire and Humber'

  // North West
  const nwPatterns = [
    'blackburn', 'blackpool', 'bolton', 'burnley', 'bury', 'carlisle',
    'chester', 'crewe', 'kendal', 'lancaster', 'liverpool', 'manchester',
    'oldham', 'preston', 'rochdale', 'salford', 'southport',
    'stockport', 'warrington', 'wigan', 'barrow', 'accrington',
    'chorley', 'failsworth', 'hyde', 'macclesfield', 'nelson',
    'northwich', 'penrith', 'st helens', 'widnes', 'workington',
    'sale', 'birkenhead', 'wallasey', 'whitehaven', 'morecambe',
    'chadderton', 'heysham',
  ]
  if (nwPatterns.some((p) => lower.includes(p))) return 'North West'

  // North East
  const nePatterns = [
    'berwick', 'darlington', 'durham', 'gateshead', 'hartlepool',
    'middlesbrough', 'newcastle', 'south shields', 'sunderland',
    'hexham', 'alnwick', 'blyth', 'bishop auckland', 'consett',
    'cramlington', 'redcar', 'stockton', 'whitley bay',
    'gosforth',
  ]
  if (nePatterns.some((p) => lower.includes(p))) return 'North East'

  return 'England'
}

// ── Main ─────────────────────────────────────────────────────────

async function main() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true })
  }

  console.log('=== Downloading DVSA ODS files ===\n')

  const buffers: Record<string, Buffer> = {}
  for (const [key, url] of Object.entries(ODS_URLS)) {
    buffers[key] = await downloadFile(url, `${key}.ods`)
  }

  console.log('\n=== Parsing spreadsheets ===\n')

  // Parse DRT122A (primary dataset)
  const wbA = XLSX.read(buffers.drt122a, { type: 'buffer' })
  const latestSheet = '2024-25'
  console.log(`  DRT122A: parsing "${latestSheet}" sheet...`)
  const centresA = parseA_Sheet(wbA, latestSheet)
  console.log(`  DRT122A: found ${centresA.size} centres`)

  // Historical data (5 years: 2024-25, 2023-24, 2022-23, 2021-22, 2020-21)
  // Skip 2020-21 as it was heavily impacted by COVID
  const historyYears = ['2019-20', '2021-22', '2022-23', '2023-24', '2024-25']
  console.log(`  DRT122A: extracting historical pass rates for ${historyYears.length} years...`)
  const historyData = extractHistoricalRates(wbA, historyYears)

  // Parse DRT122B (cancellations)
  const wbB = XLSX.read(buffers.drt122b, { type: 'buffer' })
  console.log(`  DRT122B: parsing "${latestSheet}" sheet...`)
  const centresB = parseB_Sheet(wbB, latestSheet)
  console.log(`  DRT122B: found ${centresB.size} centres`)

  // Parse DRT122C (first-attempt)
  const wbC = XLSX.read(buffers.drt122c, { type: 'buffer' })
  console.log(`  DRT122C: parsing "${latestSheet}" sheet...`)
  const centresC = parseC_Sheet(wbC, latestSheet)
  console.log(`  DRT122C: found ${centresC.size} centres`)

  // Parse DRT122D (by age)
  const wbD = XLSX.read(buffers.drt122d, { type: 'buffer' })
  console.log(`  DRT122D: parsing "${latestSheet}" sheet...`)
  const centresD = parseD_Sheet(wbD, latestSheet)
  console.log(`  DRT122D: found ${centresD.size} centres`)

  // Parse DRT122E (automatic)
  const wbE = XLSX.read(buffers.drt122e, { type: 'buffer' })
  console.log(`  DRT122E: parsing "${latestSheet}" sheet...`)
  const centresE = parseE_Sheet(wbE, latestSheet)
  console.log(`  DRT122E: found ${centresE.size} centres`)

  // ── Merge all data ──

  console.log('\n=== Merging data ===\n')

  // Calculate national average from DRT122A data
  const allRates = Array.from(centresA.values()).map((c) => c.passRateOverall)
  const nationalAverage = Math.round((allRates.reduce((sum, r) => sum + r, 0) / allRates.length) * 10) / 10

  console.log(`  National average pass rate: ${nationalAverage}%`)

  // Build merged centre list
  const mergedCentres: DvsaCentre[] = []
  let unmatchedB = 0
  let unmatchedC = 0
  let unmatchedD = 0
  let unmatchedE = 0

  for (const [name, aData] of centresA) {
    const bData = centresB.get(name)
    const cData = centresC.get(name)
    const dData = centresD.get(name)
    const eData = centresE.get(name)
    const history = historyData.get(name)

    if (!bData) unmatchedB++
    if (!cData) unmatchedC++
    if (!dData) unmatchedD++
    if (!eData) unmatchedE++

    mergedCentres.push({
      name,
      slug: toSlug(name),
      region: detectRegion(name),
      latitude: 0,
      longitude: 0,
      nearbyCentres: [],
      passRateOverall: aData.passRateOverall,
      passRateMale: aData.passRateMale,
      passRateFemale: aData.passRateFemale,
      passRateFirstAttempt: cData?.passRateFirstAttempt ?? null,
      passRateFirstAttemptMale: cData?.passRateFirstAttemptMale ?? null,
      passRateFirstAttemptFemale: cData?.passRateFirstAttemptFemale ?? null,
      passRateAutomatic: eData ?? null,
      passRateByAge: dData ?? {},
      passRateHistory: history ?? [],
      testsConductedTotal: aData.testsConductedTotal,
      testsConductedMale: aData.testsConductedMale,
      testsConductedFemale: aData.testsConductedFemale,
      zeroFaultPasses: cData?.zeroFaultPasses ?? null,
      cancellations: bData
        ? {
            dvsaCancelled: bData.dvsaCancelled,
            candidateCancelled: bData.candidateCancelled,
            noShows: bData.noShows,
          }
        : null,
      dataPeriod: 'April 2024 - March 2025',
      nationalAverage,
      difficultyRank: 0, // calculated below
      difficultyLabel: '', // calculated below
      totalRoutes: null,
    })
  }

  // Sort by pass rate (ascending = hardest first) and assign ranks
  const sorted = [...mergedCentres].sort((a, b) => a.passRateOverall - b.passRateOverall)
  for (let i = 0; i < sorted.length; i++) {
    sorted[i] = { ...sorted[i], difficultyRank: i + 1 }
  }

  // Assign difficulty labels (thirds)
  const thirdSize = Math.ceil(sorted.length / 3)
  for (let i = 0; i < sorted.length; i++) {
    const label =
      i < thirdSize
        ? 'Below Average'
        : i < thirdSize * 2
          ? 'Average'
          : 'Above Average'
    sorted[i] = { ...sorted[i], difficultyLabel: label }
  }

  // Sort final output alphabetically by name
  sorted.sort((a, b) => a.name.localeCompare(b.name))

  console.log(`  Total centres merged: ${sorted.length}`)
  console.log(`  Unmatched in DRT122B (cancellations): ${unmatchedB}`)
  console.log(`  Unmatched in DRT122C (first-attempt): ${unmatchedC}`)
  console.log(`  Unmatched in DRT122D (by age): ${unmatchedD}`)
  console.log(`  Unmatched in DRT122E (automatic): ${unmatchedE}`)

  // ── Write output ──

  const outputPath = path.join(DATA_DIR, 'centres.json')
  fs.writeFileSync(outputPath, JSON.stringify(sorted, null, 2))
  console.log(`\n=== Output written to ${outputPath} ===`)
  console.log(`  File size: ${(fs.statSync(outputPath).size / 1024).toFixed(1)} KB`)

  // ── Verification ──

  console.log('\n=== Verification ===\n')
  console.log(`  Total centres: ${sorted.length}`)
  console.log(`  National average: ${nationalAverage}%`)

  const rates = sorted.map((c) => c.passRateOverall)
  console.log(`  Min pass rate: ${Math.min(...rates)}% (${sorted.find((c) => c.passRateOverall === Math.min(...rates))?.name})`)
  console.log(`  Max pass rate: ${Math.max(...rates)}% (${sorted.find((c) => c.passRateOverall === Math.max(...rates))?.name})`)

  // Sample records
  const sampleIndices = [0, Math.floor(sorted.length / 2), sorted.length - 1]
  console.log('\n  Sample records:')
  for (const idx of sampleIndices) {
    const c = sorted[idx]
    console.log(`\n  --- ${c.name} (${c.slug}) ---`)
    console.log(`    Region: ${c.region}`)
    console.log(`    Pass rate: ${c.passRateOverall}% (M: ${c.passRateMale}%, F: ${c.passRateFemale}%)`)
    console.log(`    Tests conducted: ${c.testsConductedTotal}`)
    console.log(`    First attempt: ${c.passRateFirstAttempt ?? 'N/A'}%`)
    console.log(`    Automatic: ${c.passRateAutomatic ?? 'N/A'}%`)
    console.log(`    Zero-fault passes: ${c.zeroFaultPasses ?? 'N/A'}`)
    console.log(`    Difficulty: #${c.difficultyRank} (${c.difficultyLabel})`)
    console.log(`    Age rates: ${JSON.stringify(c.passRateByAge)}`)
    console.log(`    History: ${c.passRateHistory.map((h) => `${h.year}: ${h.rate}%`).join(', ')}`)
    console.log(`    Cancellations: ${c.cancellations ? `DVSA=${c.cancellations.dvsaCancelled}` : 'N/A'}`)
  }
}

main().catch((err) => {
  console.error('FATAL:', err)
  process.exit(1)
})
