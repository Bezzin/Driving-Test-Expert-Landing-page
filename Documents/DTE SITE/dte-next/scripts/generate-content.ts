import * as fs from 'fs'
import * as path from 'path'
import type { DvsaCentre } from '../lib/dvsa-types'

// ── Types ──────────────────────────────────────────────────────

interface CentreContent {
  slug: string
  name: string
  areaDescription: string
  keyChallenges: string[]
  specificTips: string[]
  bestTimeToTest: string
  roadTypes: string[]
  difficultyAnalysis: string
}

// ── Seeded PRNG (deterministic, no external deps) ──────────────

function createRng(seed: number) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff
    return s / 0x7fffffff
  }
}

function hashString(str: string): number {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash + str.charCodeAt(i)) & 0x7fffffff
  }
  return hash
}

function shuffle<T>(arr: readonly T[], rng: () => number): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    const temp = copy[i]
    copy[i] = copy[j]
    copy[j] = temp
  }
  return copy
}

function pick<T>(arr: readonly T[], count: number, rng: () => number): T[] {
  const shuffled = shuffle(arr, rng)
  return shuffled.slice(0, count)
}

function pickOne<T>(arr: readonly T[], rng: () => number): T {
  return arr[Math.floor(rng() * arr.length)]
}

// ── Region-specific data ───────────────────────────────────────

interface RegionProfile {
  roadCharacteristics: string[][]  // pairs of [characteristic, alternate phrasing]
  typicalChallenges: string[]
  roadTypePool: string[]
  environmentDescriptors: string[]
  weatherNotes: string[]
  trafficDescriptors: string[]
  areaFlavour: string[]  // unique local colour phrases
}

const REGION_PROFILES: Record<string, RegionProfile> = {
  London: {
    roadCharacteristics: [
      ['heavy urban traffic with frequent stop-start driving', 'constant stop-and-go conditions through congested streets'],
      ['narrow residential streets with parked cars on both sides', 'tight side roads where parked vehicles leave minimal room'],
      ['complex one-way systems requiring confident lane discipline', 'intricate one-way networks demanding sharp lane awareness'],
      ['busy high streets with pedestrian crossings at short intervals', 'active shopping streets where pedestrian hazards are constant'],
      ['bus lanes and cycle lanes that demand constant awareness', 'dedicated bus and cycle infrastructure requiring careful lane choice'],
      ['congested junctions where hesitation is quickly punished', 'packed intersections where decisive action is essential'],
      ['multi-lane approaches to major junctions', 'stacked traffic at signal-controlled crossroads'],
      ['road surfaces worn by heavy use and frequent roadworks', 'patchy surfaces and utility works narrowing the carriageway'],
    ],
    typicalChallenges: [
      'Navigating busy multi-lane roundabouts with heavy traffic flow',
      'Dealing with aggressive lane-changing from other drivers on urban dual carriageways',
      'Managing tight turns in residential streets with limited visibility past parked vehicles',
      'Responding to cyclists filtering through traffic at junctions and traffic lights',
      'Handling bus lanes with time-restricted access and correct lane positioning',
      'Executing parallel parking in spaces between tightly parked cars on narrow streets',
      'Maintaining composure at congested crossroads with multiple traffic light phases',
      'Adapting to sudden pedestrian crossings in shopping areas with high foot traffic',
      'Giving way correctly at box junctions without blocking the intersection',
      'Making progress through amber-phase traffic lights without rushing or stalling',
    ],
    roadTypePool: ['residential', 'one-way systems', 'bus lanes', 'dual carriageway', 'roundabouts', 'multi-lane junctions', 'pedestrian zones', 'cycle lanes', 'high streets', 'controlled crossings'],
    environmentDescriptors: ['densely built-up', 'bustling metropolitan', 'fast-paced urban', 'traffic-heavy inner-city', 'highly congested', 'intensely urban'],
    weatherNotes: [
      'Rain can make already congested roads even more challenging, with reduced visibility and longer braking distances on polished urban surfaces.',
      'Urban heat-island effects mean wet roads dry faster in summer, but shaded side streets can remain slippery after rain.',
    ],
    trafficDescriptors: ['consistently heavy', 'relentless during peak hours', 'dense and unpredictable', 'intensely competitive', 'unyielding even outside rush hour'],
    areaFlavour: [
      'The constant presence of buses, delivery vans, and taxis adds layers of complexity rarely found outside the capital.',
      'London driving requires a level of awareness and assertiveness that sets it apart from most other UK centres.',
      'The sheer density of road users here means candidates must process hazards faster than at less urban centres.',
      'Pedestrian behaviour in London is less predictable than in quieter areas, with jaywalking a common occurrence.',
    ],
  },
  Scotland: {
    roadCharacteristics: [
      ['single-track roads with passing places requiring careful judgement', 'single-lane roads where passing-place protocol is part of daily driving'],
      ['steep gradients that test clutch control and hill starts', 'sharp inclines where hill-start technique is put to the test'],
      ['winding rural roads with limited forward visibility', 'twisting country roads where each bend demands caution'],
      ['urban streets with tram lines and stone-built junctions', 'city roads featuring tramway crossings and granite-kerbed corners'],
      ['roads through small towns with varying speed limits', 'routes threading through villages with frequent speed changes'],
      ['stretches of dual carriageway connecting built-up areas', 'fast-moving dual carriageways linking towns across open countryside'],
      ['exposed highland roads where weather changes in minutes', 'moorland stretches where conditions shift without warning'],
      ['loch-side roads with dramatic scenery that can distract', 'routes along water where the landscape competes for attention'],
    ],
    typicalChallenges: [
      'Managing steep hill starts on inclines common in Scottish towns and countryside',
      'Judging passing places correctly on single-track roads without hesitation',
      'Dealing with reduced visibility on bends through hilly or wooded terrain',
      'Handling crosswinds on exposed stretches of road in highland areas',
      'Navigating junctions where stone walls or hedgerows limit sightlines',
      'Responding to slow-moving agricultural vehicles on country roads',
      'Maintaining appropriate speed through villages with tight speed limit changes',
      'Coping with varied road surfaces including loose gravel at rural junctions',
      'Adapting to rapidly changing light conditions as roads pass through tree-lined sections',
      'Reading the road ahead on crests where oncoming traffic may be hidden',
    ],
    roadTypePool: ['single-track roads', 'steep hills', 'country roads', 'dual carriageway', 'roundabouts', 'residential', 'stone-built junctions', 'passing places', 'moorland roads', 'village streets'],
    environmentDescriptors: ['rugged and varied', 'scenic but demanding', 'characteristically Scottish', 'geographically diverse', 'highland-influenced', 'terrain-driven Scottish'],
    weatherNotes: [
      'Scottish weather is notoriously changeable; rain, low cloud, and strong winds can all affect driving conditions within a single test.',
      'Winter tests may involve frost or ice, particularly on quieter rural roads and shaded stretches.',
      'Coastal and highland areas see weather fronts arrive quickly, so candidates should be prepared for sudden changes.',
    ],
    trafficDescriptors: ['lighter than major English cities but unpredictable on rural roads', 'moderate in urban areas with quieter rural stretches', 'sparse on country roads but requiring constant vigilance', 'seasonal with tourist traffic peaking in summer months'],
    areaFlavour: [
      'The combination of terrain and weather makes Scottish driving a uniquely comprehensive test of vehicle control.',
      'Scotland\'s road network reflects its geography: compact towns connected by roads that wind through dramatic landscapes.',
      'Even centres in Scottish cities feature gradients that would be unusual in flatter parts of England.',
      'The presence of livestock, walkers, and cyclists on rural roads adds hazards not found on urban test routes.',
    ],
  },
  Wales: {
    roadCharacteristics: [
      ['mountain roads with steep gradients and hairpin bends', 'hill roads where sharp switchbacks test steering and speed control'],
      ['narrow lanes bordered by high hedgerows limiting visibility', 'hedge-lined lanes where forward sight is measured in metres'],
      ['roads through valleys with tight turns and changing elevations', 'valley routes that climb, descend, and twist without respite'],
      ['bilingual road signage requiring quick reading and comprehension', 'dual-language signs that add a fraction of processing time at speed'],
      ['coastal roads with exposed sections and varying conditions', 'seaside stretches where wind and spray affect handling'],
      ['rural roads shared with agricultural vehicles and livestock', 'farm-country lanes where tractors and sheep are routine hazards'],
      ['river-crossing roads with narrow bridges and weight limits', 'routes that ford streams or cross stone bridges barely wider than a car'],
      ['quarry and industrial roads in former mining areas', 'post-industrial roads with uneven surfaces and heavy lorry traffic'],
    ],
    typicalChallenges: [
      'Handling steep descents requiring proper gear selection and braking technique',
      'Reading bilingual road signs quickly without losing focus on the road ahead',
      'Negotiating narrow lanes where passing oncoming vehicles requires careful manoeuvring',
      'Managing hill starts on gradients steeper than those found in flatter parts of the UK',
      'Dealing with livestock on or near the road, particularly sheep in rural areas',
      'Adjusting speed for sudden bends on valley roads with limited forward visibility',
      'Maintaining lane discipline on roads with worn or faded markings',
      'Coping with exposed mountain stretches where crosswinds affect vehicle stability',
      'Reversing into passing places when meeting oncoming traffic on single-width lanes',
      'Timing overtakes of slow vehicles on roads with few safe passing opportunities',
    ],
    roadTypePool: ['mountain roads', 'narrow lanes', 'steep hills', 'country roads', 'roundabouts', 'residential', 'dual carriageway', 'coastal roads', 'valley roads', 'bridge crossings'],
    environmentDescriptors: ['hilly and atmospheric', 'rugged Welsh', 'elevation-heavy', 'scenic but challenging', 'valley-cut and mountainous', 'distinctly Welsh'],
    weatherNotes: [
      'Welsh weather brings frequent rain, particularly in the west, making road surfaces slippery and reducing visibility.',
      'Mountain areas may experience fog and low cloud, especially during autumn and winter months.',
      'Atlantic weather systems hit Wales first, meaning conditions can deteriorate faster than forecasts suggest.',
    ],
    trafficDescriptors: ['lighter outside major towns', 'seasonal with tourist traffic in summer', 'generally moderate', 'sparse on mountain roads but with agricultural hazards', 'steady in valley towns during working hours'],
    areaFlavour: [
      'Welsh roads reward drivers who are confident with manual gearboxes, as constant gear changes are the norm on hilly routes.',
      'The bilingual signage adds a subtle but real cognitive load that candidates should practise for in advance.',
      'Even in more urban parts of Wales, gradients are a persistent feature that flatten-area drivers may underestimate.',
      'The rhythm of Welsh driving is defined by the terrain: climb, descend, turn, repeat.',
    ],
  },
  'North East': {
    roadCharacteristics: [
      ['industrial-era road layouts with tight junctions and limited visibility', 'Victorian-era street patterns creating awkward junction angles'],
      ['ring roads carrying fast-moving traffic between towns', 'orbital routes where merging speed and lane choice are critical'],
      ['coastal roads with exposed stretches and variable conditions', 'North Sea coastal routes subject to sudden wind gusts and spray'],
      ['residential estates with speed bumps and mini-roundabouts', 'post-war housing estates with traffic calming at every turn'],
      ['A-roads connecting market towns with varying speed limits', 'arterial routes threading through villages with 30 mph pinch points'],
      ['urban streets with on-street parking narrowing the carriageway', 'terraced-street driving where parked cars create a continuous slalom'],
      ['bridge crossings over the Tyne and Wear rivers', 'river crossings that funnel traffic into narrow, busy corridors'],
      ['former colliery roads with uneven surfaces and blind crests', 'back roads through ex-mining villages with poor sightlines'],
    ],
    typicalChallenges: [
      'Merging onto fast-moving ring roads from short slip roads',
      'Navigating complex junctions in town centres with multiple lanes',
      'Dealing with wet road surfaces that are common in the north-east climate',
      'Handling roundabouts at A-road junctions with high-speed traffic',
      'Managing lane changes on dual carriageways alongside heavy goods vehicles',
      'Responding to pedestrians in busy town centre shopping areas',
      'Adjusting driving for industrial areas with large vehicles entering and exiting premises',
      'Maintaining concentration on long straight stretches between towns',
      'Coping with crosswinds on exposed elevated roads and bridge approaches',
      'Timing right turns across busy dual carriageways at staggered junctions',
    ],
    roadTypePool: ['residential', 'ring roads', 'dual carriageway', 'roundabouts', 'A-roads', 'industrial roads', 'mini-roundabouts', 'coastal roads', 'bridge approaches', 'terraced streets'],
    environmentDescriptors: ['industrial heritage', 'typically northern', 'mixed urban and semi-rural', 'working-class and practical', 'industrially rooted', 'compact and well-connected'],
    weatherNotes: [
      'The north-east is one of the cooler and windier parts of England, with rain common year-round. Winter conditions can be harsh, particularly inland.',
      'North Sea winds bring a chill factor that affects road grip earlier in autumn and later into spring than in southern England.',
    ],
    trafficDescriptors: ['moderate with peaks during commute hours', 'steady on A-roads', 'variable between urban and rural areas', 'heavier near Tyneside and Wearside', 'lighter in rural Northumberland'],
    areaFlavour: [
      'North-east roads reflect the region\'s heritage: functional, direct, and occasionally challenging in their simplicity.',
      'The combination of industrial roads and open countryside means test routes here cover a genuine range of driving scenarios.',
      'Driving conditions in the north-east prepare candidates well for real-world motoring in less forgiving weather.',
      'The compact nature of north-east towns means test routes pack varied challenges into relatively short distances.',
    ],
  },
  'North West': {
    roadCharacteristics: [
      ['busy motorway junctions near major cities', 'high-volume motorway interchanges where lane discipline is paramount'],
      ['industrial areas with narrow roads and heavy goods vehicle traffic', 'mill-town streets where HGVs and cars compete for limited width'],
      ['residential streets in densely populated suburbs', 'tightly packed terraced rows with on-street parking on both sides'],
      ['ring roads connecting satellite towns to city centres', 'orbital roads carrying commuter traffic at dual-carriageway speeds'],
      ['rural roads in Lancashire and Cumbria with steep gradients', 'Pennine-fringe roads where hills and hairpins are the norm'],
      ['dual carriageways with frequent exits and lane changes required', 'fast A-roads where missing your exit means a long diversion'],
      ['tram corridors in Greater Manchester with shared road space', 'Metrolink-adjacent streets where tram tracks cross the carriageway'],
      ['canal towpath crossings and bridge humps', 'humpback canal bridges requiring careful speed and positioning'],
    ],
    typicalChallenges: [
      'Handling multi-lane roundabouts on busy ring roads and bypasses',
      'Navigating narrow terraced streets with parked cars limiting visibility',
      'Dealing with heavy rain, which is more frequent in the north-west than most regions',
      'Managing complex junction layouts in older industrial town centres',
      'Merging with fast-moving traffic on dual carriageways near motorway connections',
      'Responding to tram lines in areas that have light rail systems',
      'Coping with steep hills in towns built on Lancashire and Pennine hillsides',
      'Adjusting speed for school zones in densely populated residential areas',
      'Reading unfamiliar road layouts where historic street patterns override modern standards',
      'Maintaining lane discipline approaching large retail park roundabouts',
    ],
    roadTypePool: ['residential', 'dual carriageway', 'roundabouts', 'ring roads', 'steep hills', 'terraced streets', 'industrial roads', 'A-roads', 'tram corridors', 'canal bridges'],
    environmentDescriptors: ['characteristically northern', 'industrially rooted', 'densely populated', 'urban-meets-Pennine', 'cotton-era and compact', 'traffic-dense and varied'],
    weatherNotes: [
      'The north-west receives some of the highest rainfall in England, making wet-weather driving skills particularly important for test candidates here.',
      'Pennine-influenced weather means conditions can differ significantly between the coast and inland areas on the same day.',
    ],
    trafficDescriptors: ['heavy in and around Manchester and Liverpool', 'moderate in smaller towns', 'congested during rush hours', 'dense near retail and business parks', 'lighter in rural Cumbria and Lancashire'],
    areaFlavour: [
      'North-west driving tests tend to be thorough, with routes that mix tight urban streets with faster connecting roads.',
      'The legacy of industrial-era road layouts means some junctions here defy modern expectations, requiring extra alertness.',
      'Rain is so common in the north-west that examiners expect candidates to handle wet conditions confidently.',
      'The close spacing of towns in Greater Manchester means test routes can cross several distinctly different driving environments.',
    ],
  },
  'West Midlands': {
    roadCharacteristics: [
      ['complex multi-lane roundabouts connecting major routes', 'large island roundabouts where lane markings are critical to safe navigation'],
      ['canal bridges with narrow approaches and limited visibility', 'humpback bridges over the canal network with blind crests'],
      ['urban sprawl with continuous built-up areas and frequent junctions', 'an almost unbroken ribbon of development with junctions every few hundred metres'],
      ['ring roads around major towns carrying fast-moving traffic', 'bypass roads where traffic speeds contrast sharply with the adjacent 30 mph zones'],
      ['residential streets in suburban estates with mini-roundabouts', 'cul-de-sac and crescent layouts typical of 1960s housing developments'],
      ['dual carriageways linking Birmingham to surrounding towns', 'arterial dual carriageways that serve as the region\'s primary corridors'],
      ['light industrial estate roads with delivery vehicles', 'trading-estate approaches where vans and lorries block sightlines'],
      ['historic market town centres with narrow medieval streets', 'older town centres where road widths reflect horse-and-cart origins'],
    ],
    typicalChallenges: [
      'Negotiating large multi-lane roundabouts with multiple exits and lane markings',
      'Crossing narrow canal bridges where only one vehicle can pass at a time',
      'Handling continuous urban driving with junctions every few hundred metres',
      'Managing lane discipline on dual carriageways with frequent exits',
      'Dealing with heavy traffic around major retail and industrial parks',
      'Responding to complex road layouts in older market town centres',
      'Navigating suburban estates with speed bumps, mini-roundabouts, and parked cars',
      'Adjusting to varying speed limits through extended built-up areas',
      'Interpreting worn lane markings on heavily trafficked roundabout approaches',
      'Yielding correctly at staggered crossroads where priority is unclear',
    ],
    roadTypePool: ['residential', 'roundabouts', 'dual carriageway', 'ring roads', 'canal bridges', 'suburban estates', 'A-roads', 'mini-roundabouts', 'industrial estates', 'market town streets'],
    environmentDescriptors: ['sprawling and industrial', 'densely developed', 'junction-heavy', 'urban-suburban', 'thoroughly Midlands', 'endlessly built-up'],
    weatherNotes: [
      'Conditions in the West Midlands are typically moderate, though autumnal fog and winter frost can affect visibility and grip on quieter roads.',
      'Mist forming over canal corridors can reduce visibility unexpectedly on certain routes.',
    ],
    trafficDescriptors: ['consistently heavy near Birmingham', 'moderate in smaller towns', 'dense on connecting dual carriageways', 'heavy around retail parks and industrial zones', 'lighter in Staffordshire and Shropshire'],
    areaFlavour: [
      'The West Midlands road network is defined by its roundabouts: mastering lane selection here is non-negotiable.',
      'Canal infrastructure creates unique driving challenges, with narrow bridges and towpath crossings appearing on many routes.',
      'The sheer continuity of urban development means there is little rest between hazards on West Midlands test routes.',
      'Driving here requires an ability to read worn road markings at speed, as heavy traffic wears paint faster than in quieter areas.',
    ],
  },
  'South East': {
    roadCharacteristics: [
      ['commuter routes carrying heavy morning and evening traffic', 'London-bound corridors that are gridlocked during peak commute times'],
      ['country lanes connecting villages with limited passing room', 'single-width lanes through the Surrey, Sussex, and Kent countryside'],
      ['motorway junction approaches requiring confident merging', 'M25, M3, and M20 junction zones where slip-road technique is tested'],
      ['roundabouts at varying scales from mini to multi-lane', 'everything from painted mini-roundabouts to five-exit traffic-light islands'],
      ['residential areas with speed restrictions and traffic calming', 'leafy suburbs with 20 mph zones, humps, and chicanes'],
      ['A-roads through market towns with pedestrian activity', 'traditional high streets where shoppers step off kerbs without warning'],
      ['rat-run shortcuts used by local commuters avoiding main roads', 'through-traffic on residential streets creating unexpected hazards'],
      ['railway crossing approaches with barriers and warning lights', 'level crossings that test patience and observation in equal measure'],
    ],
    typicalChallenges: [
      'Merging onto busy dual carriageways alongside commuter traffic',
      'Navigating country lanes where hedgerows restrict forward vision',
      'Handling fast-moving traffic at motorway junction roundabouts',
      'Dealing with cyclists on narrow country roads with limited overtaking opportunities',
      'Managing complex multi-exit roundabouts near major town centres',
      'Responding to sudden speed limit changes moving between villages and open road',
      'Executing turns at staggered crossroads in older village layouts',
      'Coping with heavy congestion near railway stations during peak travel times',
      'Adjusting to gravel and mud on road surfaces near farms and equestrian centres',
      'Queuing patiently at level crossings without creeping or misjudging the barrier timing',
    ],
    roadTypePool: ['residential', 'country lanes', 'dual carriageway', 'roundabouts', 'motorway junctions', 'A-roads', 'village roads', 'commuter routes', 'level crossings', 'suburban streets'],
    environmentDescriptors: ['affluent and well-maintained', 'commuter-belt', 'village-and-town', 'busy and fast-paced', 'commuter-sprawl', 'green-belt bordered'],
    weatherNotes: [
      'The south-east enjoys relatively mild weather, but autumn leaves and morning frost can create slippery surfaces on country lanes.',
      'Summer storms can flood dips on rural roads quickly, with standing water appearing where drainage has not kept pace with development.',
    ],
    trafficDescriptors: ['heavy during commute times', 'dense near major towns', 'moderate on rural roads outside peak hours', 'intense on London-orbital routes', 'lighter in the Kent and Sussex countryside'],
    areaFlavour: [
      'South-east driving is defined by contrast: calm village lanes one minute, multi-lane roundabout the next.',
      'The commuter mindset of local traffic means other drivers are often in a hurry, which candidates must account for.',
      'Horse riders, cyclists, and walkers share many south-east lanes, adding vulnerability considerations to every journey.',
      'The well-maintained road network here can lull candidates into overconfidence before a challenging junction appears.',
    ],
  },
  'South West': {
    roadCharacteristics: [
      ['narrow lanes with high hedgerows and blind bends', 'single-vehicle-width lanes where hedgerows tower above the roofline'],
      ['coastal roads with steep gradients and dramatic drops', 'cliff-edge routes where the camber tilts toward a steep drop-off'],
      ['tourist routes that become congested in summer months', 'holiday traffic arteries that are tranquil in winter and gridlocked in August'],
      ['rural roads shared with agricultural vehicles and horse riders', 'farm-gate roads where a combine harvester can appear around any bend'],
      ['market town streets with limited width and busy pedestrian areas', 'Cotswold and Devon market squares where parked cars leave inches of clearance'],
      ['A-roads through rolling countryside with varying speed limits', 'primary routes undulating across hills with speed limits oscillating between 30 and 60'],
      ['moorland roads across Dartmoor and Exmoor', 'open moor crossings where ponies, cattle, and sheep have right of way'],
      ['harbour-side roads with tight turns and limited manoeuvring space', 'fishing-port streets where reversing may be the only option'],
    ],
    typicalChallenges: [
      'Navigating extremely narrow lanes where reversing may be necessary to let vehicles pass',
      'Handling steep coastal hills requiring precise clutch control and correct gear selection',
      'Dealing with tourist traffic that increases significantly during summer and bank holidays',
      'Responding to horse riders and slow-moving farm vehicles on country roads',
      'Managing blind bends on lanes where hedgerows grow close to the road edge',
      'Judging speed on rolling terrain where gradients change frequently',
      'Coping with wet roads from the region\'s higher-than-average rainfall',
      'Navigating through historic market towns with narrow streets and tight corners',
      'Watching for ponies and livestock roaming freely on unfenced moorland roads',
      'Maintaining tyre grip on leaf-covered lanes during autumn months',
    ],
    roadTypePool: ['narrow lanes', 'coastal roads', 'steep hills', 'country roads', 'roundabouts', 'residential', 'A-roads', 'market town streets', 'moorland roads', 'harbour roads'],
    environmentDescriptors: ['scenic and rural', 'lane-heavy and coastal', 'tourist-friendly but driving-challenging', 'quintessentially English countryside', 'rolling-hill', 'rustic and demanding'],
    weatherNotes: [
      'The south-west receives generous rainfall, particularly in Devon and Cornwall, and coastal areas can experience strong winds that affect vehicle handling.',
      'Sea fog can roll in quickly along the coast, reducing visibility from excellent to poor within minutes.',
    ],
    trafficDescriptors: ['seasonal with summer tourist surges', 'generally moderate', 'light on rural roads outside peak season', 'surprisingly heavy on A-roads during holiday weekends', 'dominated by agricultural vehicles on back roads'],
    areaFlavour: [
      'South-west driving rewards patience: rushing on these lanes is both dangerous and counterproductive.',
      'The combination of narrow lanes and steep hills makes the south-west one of the most technically demanding regions for new drivers.',
      'Local drivers know the lanes intimately, so candidates should expect other vehicles to approach bends at speeds that seem aggressive.',
      'The beauty of the landscape is a genuine hazard here, with scenic views pulling attention away from the road at the worst moments.',
    ],
  },
  'East Midlands': {
    roadCharacteristics: [
      ['long straight roads across flat terrain requiring sustained concentration', 'ruler-straight stretches where maintaining attention is the biggest challenge'],
      ['agricultural areas with tractors and wide farm vehicles', 'fenland roads where a slow-moving beet harvester can block the entire carriageway'],
      ['dual carriageways connecting major towns at national speed limit', 'fast dual carriageways that feel closer to motorway driving than local roads'],
      ['residential estates on the edges of expanding market towns', 'new-build housing developments with unfamiliar road layouts and incomplete signage'],
      ['roundabouts at major junctions handling significant traffic volumes', 'high-throughput roundabouts where hesitation causes the most problems'],
      ['A-roads through villages with changing speed limits', 'stretches that oscillate between 60 and 30 as they pass through settlements'],
      ['distribution centre approaches with articulated lorry traffic', 'logistics-park roads where HGVs outnumber cars during working hours'],
      ['flood-prone low-lying roads near rivers', 'routes through river plains that close periodically in wet weather'],
    ],
    typicalChallenges: [
      'Maintaining focus on long, straight roads where complacency can set in',
      'Overtaking slow-moving agricultural vehicles safely on single-carriageway roads',
      'Handling exposed roads where crosswinds can catch drivers off guard',
      'Navigating roundabouts at dual carriageway intersections with fast-moving traffic',
      'Dealing with seasonal flooding on roads near rivers and low-lying areas',
      'Responding to sudden speed limit changes through small villages on A-roads',
      'Managing large goods vehicle traffic near distribution centres and industrial parks',
      'Adjusting driving for varying road surfaces between newer and older road sections',
      'Reacting to sun glare on flat, open roads where there is no shelter',
      'Reading worn lane markings at busy roundabouts serving multiple A-roads',
    ],
    roadTypePool: ['residential', 'dual carriageway', 'roundabouts', 'A-roads', 'country roads', 'flat terrain roads', 'village roads', 'industrial roads', 'fenland roads', 'distribution routes'],
    environmentDescriptors: ['flat and open', 'agricultural and industrial', 'straight-road dominated', 'market-town and countryside', 'Midlands-plain', 'spacious but deceptive'],
    weatherNotes: [
      'The East Midlands has a continental climate pattern with cold winters and warm summers. Fog can be an issue on flat, low-lying roads, particularly in autumn.',
      'Exposed flat roads amplify wind effects, making crosswind correction an everyday skill here.',
    ],
    trafficDescriptors: ['moderate overall', 'heavy near Nottingham and Leicester', 'lighter in rural areas but unpredictable with agricultural vehicles', 'dense around logistics hubs', 'steady on A-road corridors'],
    areaFlavour: [
      'East Midlands driving is deceptively straightforward: the flat roads look easy but demand constant speed discipline.',
      'The region\'s role as a distribution hub means HGV traffic is heavier here than in most comparable areas.',
      'Agricultural vehicle encounters are not a rare event here but an expected part of everyday driving.',
      'The long sightlines can tempt drivers into excessive speed, which examiners are well attuned to.',
    ],
  },
  'East of England': {
    roadCharacteristics: [
      ['flat, open roads across fenland and agricultural country', 'dead-flat fen roads stretching to the horizon without a single bend'],
      ['long straight stretches that test speed discipline', 'monotonous straights where maintaining exactly 60 mph requires active effort'],
      ['rural roads frequented by tractors and agricultural machinery', 'sugar-beet season roads where slow vehicles are an hourly occurrence'],
      ['commuter routes linking towns to London with heavy peak traffic', 'London-bound A-roads carrying volume that belies their single-carriageway status'],
      ['market town centres with narrow, historic road layouts', 'medieval-grid town centres where modern vehicles barely fit the streets'],
      ['coastal roads along the Norfolk and Suffolk shoreline', 'seafront roads subject to wind, occasional flooding, and tourist congestion'],
      ['B-roads through arable farmland with few landmarks', 'featureless farm roads where navigation relies on road signs alone'],
      ['level crossings on busy railway lines to London', 'barrier-controlled crossings that halt traffic on major routes'],
    ],
    typicalChallenges: [
      'Resisting the temptation to exceed speed limits on long, empty straight roads',
      'Dealing with crosswinds on exposed roads across flat terrain',
      'Safely passing slow-moving agricultural vehicles on single carriageways',
      'Navigating narrow streets in historic market towns with tight turning radii',
      'Handling seasonal flooding on low-lying roads near rivers and the coast',
      'Managing commuter congestion on roads connecting to London-bound routes',
      'Responding to sudden bends that break up otherwise straight road sections',
      'Coping with poor road surfaces on minor rural roads',
      'Judging distance accurately on flat roads where perspective is misleading',
      'Waiting patiently at level crossings without losing concentration',
    ],
    roadTypePool: ['residential', 'country roads', 'dual carriageway', 'roundabouts', 'A-roads', 'flat terrain roads', 'coastal roads', 'market town streets', 'fenland roads', 'level crossings'],
    environmentDescriptors: ['flat and expansive', 'agricultural and rural', 'open-sky and horizon-stretching', 'quieter than most English regions', 'fenland-influenced', 'deceptively simple'],
    weatherNotes: [
      'Eastern England is one of the drier parts of the UK, but winds from the North Sea can be strong, particularly on exposed flat roads.',
      'Morning mist and fog are common in low-lying areas, sometimes persisting until midday during autumn.',
    ],
    trafficDescriptors: ['lighter than the south-east', 'moderate in larger towns', 'sparse on rural roads but with agricultural hazards', 'surprisingly heavy on Cambridge and Norwich approaches', 'seasonal near the coast'],
    areaFlavour: [
      'East of England driving is an exercise in discipline: the easy-looking roads demand more self-regulation than complex urban junctions.',
      'The flat terrain makes overtaking judgement critical, as distances are harder to estimate without vertical reference points.',
      'Local drivers travel these roads daily at confidence-inspiring speeds that test candidates should not try to match.',
      'The region\'s quiet roads can breed overconfidence, which examiners are specifically trained to assess.',
    ],
  },
  'Yorkshire and Humber': {
    roadCharacteristics: [
      ['steep hills in Pennine towns requiring confident clutch control', 'Pennine-grade inclines where a rolled-back start earns an instant serious fault'],
      ['narrow roads with stone walls on either side limiting visibility', 'dry-stone-walled lanes creating a tunnel effect with no room for error'],
      ['narrow bridges over rivers and canals requiring careful judgement', 'single-width packhorse bridges where priority rules are essential knowledge'],
      ['industrial estate roads with heavy goods vehicles', 'steel-works and warehouse approaches where articulated lorries dominate'],
      ['residential streets in densely built terraced housing areas', 'Victorian terrace rows where wing mirrors brush if two cars meet'],
      ['moorland roads with exposed stretches and sudden weather changes', 'Pennine-top crossings where visibility can drop from miles to metres'],
      ['steep cobbled streets in historic hill towns', 'cobblestone climbs where traction is reduced and braking distances increase'],
      ['valley-bottom roads prone to standing water after rain', 'river-valley routes where puddles form in dips faster than drainage can cope'],
    ],
    typicalChallenges: [
      'Executing hill starts on steep gradients found throughout Yorkshire\'s towns',
      'Navigating narrow roads between stone walls where passing is tight',
      'Crossing narrow bridges where priority rules must be observed',
      'Handling wet road conditions on exposed moorland roads',
      'Dealing with heavy goods vehicles on industrial estate approaches',
      'Managing roundabouts on ring roads around Yorkshire\'s major cities',
      'Responding to sudden gradient changes in hilly terrain',
      'Maintaining control in crosswinds on elevated, exposed road sections',
      'Driving on cobbled surfaces that reduce tyre grip in wet conditions',
      'Interpreting priority at unmarked junctions in older residential areas',
    ],
    roadTypePool: ['residential', 'steep hills', 'narrow bridges', 'dual carriageway', 'roundabouts', 'moorland roads', 'stone-walled lanes', 'industrial roads', 'cobbled streets', 'terraced streets'],
    environmentDescriptors: ['hilly and characterful', 'industrial yet scenic', 'Pennine-influenced', 'urban-and-moorland', 'topographically dramatic', 'gritty and varied'],
    weatherNotes: [
      'Yorkshire weather is notably variable, with rain common on the western Pennine slopes and wind a factor on moorland roads.',
      'Valley bottoms can trap cold air, creating frost and ice earlier in the season than surrounding higher ground.',
    ],
    trafficDescriptors: ['heavy in Leeds, Sheffield, and Bradford', 'moderate in smaller towns', 'light on rural moorland roads', 'dense during mill-shift changeover times', 'unpredictable on cross-Pennine routes'],
    areaFlavour: [
      'Yorkshire test routes are among the most physically demanding in England, with gradients that test vehicle control to its limit.',
      'The combination of stone walls and steep lanes creates driving conditions rarely found in southern England.',
      'Even urban Yorkshire centres feature hills that would be considered unusual in flatter counties.',
      'Candidates from outside Yorkshire often underestimate the gradient challenges; local practice is strongly recommended.',
    ],
  },
  'Northern Ireland': {
    roadCharacteristics: [
      ['roads with different marking conventions from the rest of the UK', 'road markings and signage that follow conventions unique to Northern Ireland'],
      ['border roads connecting Northern Ireland to the Republic', 'cross-border routes where road standards can change without warning'],
      ['rural roads through farmland with limited forward visibility', 'green-hedged farm roads where every gateway could conceal a tractor'],
      ['urban streets in cities with varying road layouts', 'Belfast and Derry streets mixing Victorian-era and modern road designs'],
      ['dual carriageways connecting major towns', 'high-speed connecting roads that form the backbone of the NI network'],
      ['coastal roads along the Antrim and Down coastlines', 'spectacular coastal routes where the scenery is matched by the driving challenge'],
      ['drumlin-country roads with constant undulations', 'rolling terrain roads that dip and rise without straight or level sections'],
      ['country roads with grassy centres and soft verges', 'little-used lanes where vegetation encroaches from both sides'],
    ],
    typicalChallenges: [
      'Adapting to road marking and signage conventions that differ slightly from GB',
      'Navigating rural roads where hedgerows and ditches line both sides',
      'Handling steep hills in areas around the Mourne Mountains and Antrim Glens',
      'Dealing with agricultural vehicles on country roads between towns',
      'Managing junctions in older town centres with irregular layouts',
      'Responding to weather conditions that change rapidly, especially near the coast',
      'Coping with limited visibility on twisting rural roads through drumlin countryside',
      'Maintaining lane discipline on dual carriageways with fast-moving traffic',
      'Judging gaps in traffic at junctions where approach speeds are high',
      'Handling soft verges that can pull a wheel if positioning is not precise',
    ],
    roadTypePool: ['residential', 'country roads', 'dual carriageway', 'roundabouts', 'border roads', 'coastal roads', 'steep hills', 'rural lanes', 'drumlin roads', 'urban streets'],
    environmentDescriptors: ['uniquely Northern Irish', 'green and undulating', 'drumlin-sculpted', 'rural-urban blended', 'convention-distinct', 'characteristically Irish'],
    weatherNotes: [
      'Northern Ireland experiences frequent rainfall and wind, particularly in coastal areas. Conditions can change quickly, so adaptability is key.',
      'Atlantic weather systems arrive here first, meaning morning forecasts are often outdated by test time.',
    ],
    trafficDescriptors: ['moderate in Belfast and Derry', 'light in rural areas', 'steady on connecting dual carriageways', 'heavier than expected near shopping centres', 'influenced by cross-border traffic patterns'],
    areaFlavour: [
      'Northern Ireland\'s driving test has its own character, reflecting road conventions and conditions unique to the province.',
      'The combination of drumlin terrain and unpredictable weather makes NI driving a genuine test of adaptability.',
      'Cross-border road quality differences catch some candidates off guard, though test routes remain within NI.',
      'Local driving culture here is generally more courteous than in major English cities, but the roads themselves are no less challenging.',
    ],
  },
  England: {
    roadCharacteristics: [
      ['a variety of road types typical of English towns and countryside', 'a representative mix of the roads found across England'],
      ['residential areas with parked cars and speed restrictions', 'housing-estate roads where traffic calming and parking dominate'],
      ['dual carriageways connecting built-up areas', 'fast connecting roads that test higher-speed confidence'],
      ['roundabouts at various scales from mini to large multi-lane', 'roundabouts of every description from painted circles to signalised gyratories'],
      ['A-roads through villages with varying speed limits', 'through-routes that alternate between national speed limit and village 30 zones'],
      ['country lanes with limited visibility around bends', 'quiet rural roads where blind corners demand cautious speed'],
    ],
    typicalChallenges: [
      'Handling roundabouts of different sizes and traffic volumes',
      'Navigating residential streets with parked cars creating pinch points',
      'Managing speed changes between built-up areas and open road',
      'Dealing with dual carriageway driving at higher speeds',
      'Responding to pedestrians and cyclists in urban environments',
      'Maintaining concentration through varied driving conditions',
      'Executing manoeuvres in realistic on-road situations',
      'Coping with weather-related changes to road conditions',
    ],
    roadTypePool: ['residential', 'dual carriageway', 'roundabouts', 'A-roads', 'country lanes', 'village roads', 'mini-roundabouts', 'urban streets'],
    environmentDescriptors: ['varied and typical', 'characteristically English', 'mixed urban-rural', 'moderately busy', 'representative English', 'well-rounded'],
    weatherNotes: ['English weather is famously variable, so be prepared for rain, wind, or bright sun on any test day.'],
    trafficDescriptors: ['moderate overall', 'variable by time of day', 'typical of English towns'],
    areaFlavour: [
      'This centre offers a well-rounded test that covers the full range of everyday driving situations.',
      'The driving conditions here are typical of middle England, providing a fair assessment of practical ability.',
    ],
  },
}

// ── Opening line templates ─────────────────────────────────────

// Helper: pick correct article for a phrase ("a" vs "an" vs nothing if it starts with "a ")
function article(phrase: string): string {
  const lower = phrase.toLowerCase().trim()
  // If it already starts with "a " or "an " or a determiner, skip the article
  if (/^(a |an |the |its |one |this )/.test(lower)) return ''
  if (/^[aeiou]/.test(lower)) return 'an '
  return 'a '
}

const OPENING_TEMPLATES: Array<(c: DvsaCentre, env: string, flavour: string) => string> = [
  (c, env) => `Situated in the heart of ${c.region}, the ${c.name} test centre serves learners navigating ${article(env)}${env} driving environment.`,
  (c, env) => `Serving learner drivers across the ${c.name} area, this ${env} test centre presents its own distinct set of challenges.`,
  (c, env) => `${c.name} offers candidates ${article(env)}${env} test experience shaped by the character of ${c.region}.`,
  (c, env) => `Known for its ${env} road network, the ${c.name} driving test centre draws candidates from across the surrounding area.`,
  (c, env) => `Learners heading to ${c.name} will encounter ${article(env)}${env} environment that reflects the broader driving conditions of ${c.region}.`,
  (c, env) => `The ${c.name} test centre sits within ${article(env)}${env} area, presenting candidates with a driving test firmly rooted in local road conditions.`,
  (c, env) => `For those taking their practical test at ${c.name}, the surrounding ${env} roads offer a thorough examination of driving ability.`,
  (c, env) => `Positioned in ${c.region}, ${c.name} provides a driving test experience defined by ${env} road characteristics.`,
  (c, env) => `Candidates at the ${c.name} centre face a test shaped by the ${env} roads and junctions that surround it.`,
  (c, env) => `The driving test at ${c.name} takes place across ${article(env)}${env} network of roads typical of the ${c.region} area.`,
  (c, env) => `Among the test centres in ${c.region}, ${c.name} stands out for its ${env} road layout and the challenges it presents.`,
  (c, env) => `Taking your test at ${c.name} means tackling ${article(env)}${env} road network where local knowledge can make a real difference.`,
  (c, env) => `The ${c.name} practical driving test covers ${article(env)}${env} mix of roads that puts candidates through their paces.`,
  (c, env) => `Located in ${c.region}, the ${c.name} centre tests drivers across ${env} terrain that demands careful preparation.`,
  (c, env) => `${c.name} is a ${c.region} test centre where candidates encounter ${env} conditions from the moment they leave the car park.`,
  (c, env) => `Preparing for your test at ${c.name} requires understanding the ${env} driving environment that defines this part of ${c.region}.`,
  (c, env) => `The roads around ${c.name} present ${article(env)}${env} challenge that is characteristic of the wider ${c.region} region.`,
  (c, env) => `At ${c.name}, the practical test routes wind through ${env} roads that reflect the everyday driving conditions of the area.`,
  (c, env) => `${c.name} is one of ${c.region}'s test centres where the ${env} surroundings ensure a varied and realistic assessment.`,
  (c, env) => `Drivers sitting their test at ${c.name} should expect ${article(env)}${env} mix of road types representative of ${c.region}.`,
  (c, env) => `Nestled in ${c.region}, the ${c.name} centre provides a practical test across ${env} roads and diverse junctions.`,
  (c, env) => `The test experience at ${c.name} is shaped by ${article(env)}${env} landscape, making thorough preparation essential.`,
  (c, env) => `Approaching your practical test at ${c.name}, you will find ${article(env)}${env} road environment that tests a broad range of skills.`,
  (c, env) => `As one of the established centres in ${c.region}, ${c.name} offers ${article(env)}${env} test that reflects genuine local driving conditions.`,
  (c, env, fl) => `${c.name} test centre exposes candidates to the ${env} conditions that make driving in ${c.region} distinctive. ${fl}`,
  (c, env, fl) => `The ${c.name} area presents ${article(env)}${env} test environment. ${fl}`,
  (c, env) => `With ${c.testsConductedTotal.toLocaleString()} tests conducted in the last year, ${c.name} is ${c.testsConductedTotal > 5000 ? 'one of the busier' : c.testsConductedTotal < 1500 ? 'one of the quieter' : 'a moderately busy'} centres in ${c.region}.`,
  (c, env) => `${c.name} sits in ${article(env)}${env} pocket of ${c.region}, where the test routes reflect genuine local driving conditions rather than a sanitised examination course.`,
  (c, env) => `Ranked ${c.difficultyRank} out of 322 UK test centres for difficulty, ${c.name} presents ${article(env)}${env} challenge in the ${c.region} region.`,
  (c, env) => `Few test centres capture the character of ${c.region} quite like ${c.name}, where ${env} conditions define every minute of the practical exam.`,
]

// ── Pass rate bracket analysis ─────────────────────────────────

function getPassRateBracket(rate: number): { tone: string; descriptor: string; advice: string } {
  if (rate < 40) {
    return {
      tone: 'challenging',
      descriptor: 'one of the more demanding centres in the country',
      advice: 'Thorough preparation is essential here. Candidates should aim for well above the minimum standard to give themselves the best chance of success.',
    }
  }
  if (rate < 50) {
    return {
      tone: 'moderately challenging',
      descriptor: 'a moderately challenging centre where solid preparation pays off',
      advice: 'Focused practice on the specific challenges of this area will help candidates build the confidence needed to pass.',
    }
  }
  if (rate < 60) {
    return {
      tone: 'average',
      descriptor: 'a centre with roughly average difficulty',
      advice: 'Candidates who are well-prepared and familiar with the local road types should approach their test with reasonable confidence.',
    }
  }
  return {
    tone: 'favourable',
    descriptor: 'one of the more favourable centres in terms of pass rates',
    advice: 'While the statistics are encouraging, solid preparation remains important. The pass rate reflects the conditions rather than an easy test.',
  }
}

// ── Trend analysis ─────────────────────────────────────────────

function analyseTrend(history: Array<{ year: string; rate: number }>): string {
  if (history.length < 2) return 'Limited historical data is available for this centre, so trend analysis is not possible.'

  const first = history[0].rate
  const last = history[history.length - 1].rate
  const diff = last - first
  const recentTwo = history.slice(-2)
  const recentDiff = recentTwo.length === 2 ? recentTwo[1].rate - recentTwo[0].rate : 0

  if (diff > 5 && recentDiff > 0) {
    return `Pass rates here have shown a notable upward trend, rising from ${first}% in ${history[0].year} to ${last}% in ${history[history.length - 1].year}, an improvement of ${Math.abs(diff).toFixed(1)} percentage points over the period.`
  }
  if (diff > 2) {
    return `Pass rates have improved modestly over recent years, moving from ${first}% to ${last}%, a gradual gain of ${diff.toFixed(1)} percentage points.`
  }
  if (diff < -5 && recentDiff < 0) {
    return `Pass rates have declined from ${first}% in ${history[0].year} to ${last}% most recently, a drop of ${Math.abs(diff).toFixed(1)} percentage points that suggests candidates should prepare even more thoroughly.`
  }
  if (diff < -2) {
    return `There has been a slight decline in pass rates over the recorded period, from ${first}% down to ${last}%, a shift of ${Math.abs(diff).toFixed(1)} points.`
  }
  return `Pass rates have remained relatively stable over the recorded period, fluctuating between ${Math.min(...history.map(h => h.rate))}% and ${Math.max(...history.map(h => h.rate))}%, a range of just ${(Math.max(...history.map(h => h.rate)) - Math.min(...history.map(h => h.rate))).toFixed(1)} percentage points.`
}

// ── Age insight generation ─────────────────────────────────────

function getAgeInsights(ageData: Record<string, number>, rng: () => number): string[] {
  const insights: string[] = []
  const ages = Object.entries(ageData).map(([age, rate]) => ({ age: parseInt(age, 10), rate }))
  if (ages.length === 0) return insights

  const sorted = [...ages].sort((a, b) => b.rate - a.rate)
  const best = sorted[0]
  const worst = sorted[sorted.length - 1]

  if (best.rate - worst.rate > 15) {
    insights.push(
      `There is a significant spread in pass rates by age here: ${best.age}-year-olds achieve ${best.rate}%, while ${worst.age}-year-olds manage only ${worst.rate}%, a gap of ${(best.rate - worst.rate).toFixed(1)} percentage points.`
    )
  }

  const youngRate = ageData['17'] ?? null
  const olderRates = ages.filter(a => a.age >= 22).map(a => a.rate)
  const avgOlder = olderRates.length > 0 ? olderRates.reduce((s, r) => s + r, 0) / olderRates.length : null

  if (youngRate !== null && avgOlder !== null) {
    if (youngRate > avgOlder + 8) {
      insights.push(`Younger candidates at 17 perform notably well here with a ${youngRate}% pass rate, compared to an average of ${avgOlder.toFixed(1)}% for those aged 22-25.`)
    } else if (avgOlder > youngRate + 5) {
      insights.push(`Interestingly, candidates aged 22-25 average ${avgOlder.toFixed(1)}% here, outperforming 17-year-olds who pass at ${youngRate}%.`)
    }
  }

  return insights
}

// ── Gender insight ─────────────────────────────────────────────

function getGenderInsight(centre: DvsaCentre): string | null {
  const diff = centre.passRateMale - centre.passRateFemale
  if (Math.abs(diff) < 3) return null
  if (diff > 5) {
    return `Male candidates pass at ${centre.passRateMale}% versus ${centre.passRateFemale}% for female candidates, a ${diff.toFixed(1)}-point gap worth noting.`
  }
  if (diff < -5) {
    return `Female candidates outperform male candidates here: ${centre.passRateFemale}% versus ${centre.passRateMale}%, a ${Math.abs(diff).toFixed(1)}-point advantage.`
  }
  if (diff > 0) {
    return `Male candidates edge ahead with ${centre.passRateMale}% compared to ${centre.passRateFemale}% for female candidates.`
  }
  return `Female candidates have a slight edge at ${centre.passRateFemale}% versus ${centre.passRateMale}% for male candidates.`
}

// ── Automatic vs manual ────────────────────────────────────────

function getAutomaticInsight(centre: DvsaCentre): string | null {
  if (centre.passRateAutomatic === null) return null
  const diff = centre.passRateOverall - centre.passRateAutomatic
  if (diff > 8) {
    return `Automatic test candidates pass at just ${centre.passRateAutomatic}% here, a substantial ${diff.toFixed(1)}-point gap below the overall ${centre.passRateOverall}% that suggests local conditions favour manual gearbox control.`
  }
  if (diff > 3) {
    return `The automatic pass rate of ${centre.passRateAutomatic}% trails the overall ${centre.passRateOverall}% by ${diff.toFixed(1)} points, a gap automatic candidates should factor into their preparation.`
  }
  if (diff < -3) {
    return `Automatic candidates actually pass at a higher rate here (${centre.passRateAutomatic}% vs ${centre.passRateOverall}% overall), suggesting the local conditions suit automatic transmission well.`
  }
  return null
}

// ── Urban/rural classification ─────────────────────────────────

function classifyUrbanRural(centre: DvsaCentre): 'urban' | 'suburban' | 'semi-rural' | 'rural' {
  const name = centre.name.toLowerCase()
  const slug = centre.slug

  if (centre.region === 'London') return 'urban'
  if (centre.testsConductedTotal > 8000) return 'urban'

  const suburbanEndings = ['bury', 'field', 'ley', 'stead', 'ham', 'ton', 'worth']
  const hasSuburbanEnding = suburbanEndings.some(e => slug.endsWith(e))
  const hasParenthetical = name.includes('(')
  const hasDirection = /\b(north|south|east|west)\b/i.test(name)

  if (centre.testsConductedTotal > 4000) return 'suburban'
  if (hasParenthetical || hasDirection) return 'suburban'
  if (hasSuburbanEnding && centre.testsConductedTotal > 2000) return 'suburban'

  if (centre.testsConductedTotal < 800) return 'rural'
  if (centre.region === 'Scotland' && centre.testsConductedTotal < 1500) return 'semi-rural'

  return 'semi-rural'
}

// ── Best time to test ──────────────────────────────────────────

function getBestTimeToTest(centre: DvsaCentre, rng: () => number): string {
  const classification = classifyUrbanRural(centre)

  // Build a unique sentence using centre data
  const volume = centre.testsConductedTotal
  const volumeNote = volume > 6000
    ? `With ${volume.toLocaleString()} tests conducted annually, this is a high-volume centre where test slots fill quickly.`
    : volume < 1500
      ? `As a quieter centre with ${volume.toLocaleString()} tests per year, availability is generally better here than at busier locations.`
      : ''

  const urbanTimes = [
    `Mid-morning tests between 10am and 12pm typically avoid the worst of commuter traffic around ${centre.name}, giving candidates calmer roads to work with.`,
    `Early afternoon slots around 1pm to 2:30pm tend to offer lighter traffic at ${centre.name}, as the morning rush has cleared and the school run has not yet begun.`,
    `Booking a test mid-week at ${centre.name}, particularly on a Tuesday or Wednesday, often means quieter roads compared to Monday mornings and Friday afternoons.`,
  ]

  const ruralTimes = [
    `Tests during standard working hours at ${centre.name} generally offer the most predictable conditions, avoiding darker winter evenings and any overnight frost residue.`,
    `Summer months at ${centre.name} offer the best visibility and road conditions, though learners should be aware of increased seasonal traffic during this period.`,
    `Mid-morning appointments at ${centre.name} tend to provide good road conditions after any overnight frost has cleared, particularly during autumn and winter.`,
  ]

  const suburbanTimes = [
    `Avoiding school run times (8:15-9:15am and 2:45-3:30pm) near ${centre.name} can make a noticeable difference to traffic levels in the surrounding residential areas.`,
    `Late morning tests at ${centre.name} benefit from lighter traffic after the commuter rush while still offering good daylight.`,
    `Midweek tests at ${centre.name} tend to have calmer traffic conditions than Monday or Friday slots, giving candidates a less pressured environment.`,
  ]

  let timeTip: string
  if (classification === 'urban') timeTip = pickOne(urbanTimes, rng)
  else if (classification === 'rural' || classification === 'semi-rural') timeTip = pickOne(ruralTimes, rng)
  else timeTip = pickOne(suburbanTimes, rng)

  return volumeNote ? `${timeTip} ${volumeNote}` : timeTip
}

// ── Tip generation ─────────────────────────────────────────────

function generateTips(centre: DvsaCentre, profile: RegionProfile, rng: () => number): string[] {
  const tips: string[] = []
  const classification = classifyUrbanRural(centre)

  // Region-specific tips (keyed to EVERY region)
  const regionTips: Record<string, string[]> = {
    London: [
      'Practise mirror-signal-manoeuvre religiously in heavy traffic; examiners at London centres pay close attention to observation in congested conditions.',
      'Get comfortable with bus lane rules, including the times they are active and when you may legally use them.',
      'Expect cyclists appearing in blind spots at junctions. Always check mirrors and shoulder before turning.',
      'Practise driving on narrow streets where you may need to give way to oncoming traffic between parked cars.',
      'Build confidence with busy roundabouts by practising at different times of day around your centre.',
      'Learn to read complex junction road markings quickly, as hesitation at junctions is a common fault at London centres.',
      'Practise pulling away from traffic lights swiftly but safely, as slow starts can frustrate following traffic in the capital.',
    ],
    Scotland: [
      'Dedicate extra practice time to hill starts, as even urban Scottish centres typically feature significant gradients.',
      'Familiarise yourself with passing place etiquette if the test routes include any single-track sections near your centre.',
      'Practise clutch control at low speed, essential for the tight turns and gradients common around Scottish test centres.',
      'Be prepared for rapid weather changes during your test. Adjusting your driving for rain or wind is expected at Scottish centres.',
      'Get comfortable with varying road surfaces, as roads near your centre may transition between smoother and rougher sections.',
      'Practise driving on roads where visibility is limited by terrain, adjusting your speed accordingly.',
      'Build confidence with overtaking slower vehicles safely on single-carriageway A-roads.',
    ],
    Wales: [
      'Spend extra time on hill starts and controlled descents, as gradients around Welsh centres can be steep.',
      'Practise reading road signs quickly, including bilingual Welsh-English signs that may take a moment longer to process.',
      'Get comfortable with narrow lanes where you may need to reverse to a passing place.',
      'Prepare for variable weather conditions, particularly rain, which is common throughout Wales.',
      'Practise gear selection for descents to maintain control without over-relying on your brakes.',
      'Build experience on roads where livestock may be present, knowing how to respond calmly and safely.',
      'Learn to judge the width of your car precisely; narrow Welsh lanes leave little margin for error.',
    ],
    'North East': [
      'Practise merging onto ring roads from short slip roads, as this is a common route feature in the north-east.',
      'Get used to driving in wet conditions, which are frequent in this region throughout the year.',
      'Build confidence with roundabouts at A-road junctions where traffic moves at higher speeds.',
      'Practise navigating terraced streets with cars parked on both sides limiting your forward visibility.',
      'Work on lane discipline for multi-lane approaches to town centre junctions.',
      'Get comfortable with coastal road conditions if your centre is near the coast.',
      'Practise responding to large vehicles at industrial area junctions near your centre.',
    ],
    'North West': [
      'Practise wet-weather driving, as the north-west has some of the highest rainfall in England.',
      'Get comfortable with multi-lane roundabouts, which feature prominently on routes around north-west centres.',
      'Build confidence navigating narrow terraced streets with parked cars on both sides.',
      'Practise merging with fast-moving traffic on dual carriageways near motorway connections.',
      'Work on hill starts if your centre is near the Pennine foothills, where gradients can catch out flat-ground drivers.',
      'Get used to tram line crossings if your centre is in the Greater Manchester Metrolink area.',
      'Practise school-zone driving, as densely populated residential areas feature heavily on north-west routes.',
    ],
    'West Midlands': [
      'Master multi-lane roundabout technique, as roundabouts are the defining junction type of West Midlands test routes.',
      'Practise crossing narrow canal bridges where only one vehicle can pass, timing your approach carefully.',
      'Build confidence with continuous urban driving where junctions come every few hundred metres.',
      'Get used to reading worn lane markings at speed, as heavy traffic wears road paint faster here than in quieter areas.',
      'Practise dual carriageway driving with frequent exit/entry slip roads.',
      'Work on speed limit awareness through extended built-up areas where limits change frequently.',
      'Build experience navigating older market town centres with narrow, irregular road layouts.',
    ],
    'South East': [
      'Practise country lane driving, as hedgerow-lined lanes feature on many south-east test routes.',
      'Build confidence merging onto dual carriageways alongside commuter traffic.',
      'Get used to the variety of roundabout sizes here, from mini-roundabouts to large multi-lane junctions.',
      'Practise adjusting speed for frequent changes between village 30 zones and national speed limit.',
      'Work on your awareness of cyclists and horse riders, who share many south-east lanes.',
      'Build experience with staggered crossroads and priority junctions in older village layouts.',
      'Practise patience at level crossings, maintaining concentration during the wait.',
    ],
    'South West': [
      'Practise driving on extremely narrow lanes where reversing may be your only option when meeting oncoming traffic.',
      'Build clutch control for the steep coastal and inland hills found around south-west centres.',
      'Get used to sharing the road with horse riders, agricultural vehicles, and seasonal tourist traffic.',
      'Practise judging the width of your vehicle in narrow lanes where hedgerows brush both sides.',
      'Work on your gear selection for descents, relying on engine braking rather than just your foot brake.',
      'Build awareness of free-roaming livestock on unfenced moorland roads.',
      'Practise wet-weather driving, as the south-west receives above-average rainfall.',
    ],
    'East Midlands': [
      'Practise maintaining concentration on long, straight roads where the temptation to lose focus is real.',
      'Build confidence overtaking slow agricultural vehicles safely on single-carriageway roads.',
      'Get used to crosswinds on exposed flat roads, keeping a firm but relaxed grip on the steering.',
      'Practise roundabout technique at dual carriageway intersections where approaching traffic moves quickly.',
      'Work on your speed discipline, as the flat, open roads here tempt many drivers to exceed limits.',
      'Build experience with the logistics-park roads near your centre where HGV traffic is heavy.',
      'Practise responding to sudden speed limit changes through villages strung along A-roads.',
    ],
    'East of England': [
      'Practise maintaining accurate speed on long straight roads where the flat terrain makes limits hard to judge.',
      'Build experience handling crosswinds, which are a genuine factor on exposed fen and coastal roads.',
      'Get comfortable safely passing agricultural vehicles, a regular occurrence on East of England roads.',
      'Practise navigating historic market town centres with tight turning radii and narrow streets.',
      'Work on your concentration stamina for featureless road stretches where attention can wander.',
      'Build experience with level crossings, which are more common in this region than in most.',
      'Practise judging overtaking distances on flat roads where perspective can be misleading.',
    ],
    'Yorkshire and Humber': [
      'Dedicate serious practice to hill starts, as Yorkshire gradients are among the steepest on UK test routes.',
      'Practise driving between stone walls where passing oncoming vehicles requires precise positioning.',
      'Build confidence crossing narrow bridges where priority rules must be observed.',
      'Get comfortable with wet-weather and crosswind driving on exposed moorland stretches.',
      'Work on your observation at unmarked junctions in older residential areas.',
      'Practise cobbled-street driving if your centre includes historic areas, as grip is reduced.',
      'Build experience navigating ring-road roundabouts with heavy commercial vehicle traffic.',
    ],
    'Northern Ireland': [
      'Familiarise yourself with Northern Ireland-specific road marking conventions that differ from GB.',
      'Practise driving on narrow rural roads where hedgerows and ditches line both sides.',
      'Build confidence with the hilly terrain found in many parts of Northern Ireland.',
      'Get used to dealing with agricultural vehicles on country roads between towns.',
      'Practise junction technique at older town centre junctions with irregular layouts.',
      'Work on adapting to rapid weather changes, a constant feature of NI driving.',
      'Build experience on dual carriageways where approach speeds can be high.',
    ],
    England: [
      'Practise roundabout technique at various sizes, from mini to multi-lane.',
      'Build confidence driving through residential areas with parked-car pinch points.',
      'Work on smooth speed transitions between 30 and 60 mph zones.',
      'Practise dual carriageway driving at appropriate speeds.',
      'Get comfortable responding to pedestrians and cyclists in mixed-use areas.',
    ],
  }

  // Classification-based tips
  const urbanTips = [
    'Practise maintaining a steady following distance in stop-start traffic without leaving gaps so large that other drivers cut in.',
    'Get comfortable with multi-lane roundabouts by understanding your lane choice well before you reach the roundabout.',
    'Build your ability to make progress when safe, as driving too slowly or timidly is itself a test fault.',
    'Practise parallel parking in realistic conditions with vehicles in front and behind your target space.',
    'Work on clutch control for the frequent slow-speed manoeuvring required in urban test routes.',
  ]

  const ruralTips = [
    'Practise judging the national speed limit on open roads. Going too slowly can be as much a fault as exceeding it.',
    'Build confidence with overtaking slow vehicles when safe, reading the road ahead for oncoming traffic.',
    'Get used to adjusting your speed for bends where you cannot see the exit.',
    'Practise responding to unexpected hazards such as animals or debris on the road.',
    'Develop your awareness of road surface changes, particularly after rain when grip may be reduced.',
  ]

  const suburbanTips = [
    'Practise driving through residential areas where parked cars create pinch points requiring you to judge priority.',
    'Get comfortable with mini-roundabouts, common in suburban areas and testing your observation and timing.',
    'Work on smooth transitions between 20, 30, and 40 mph zones, as speed changes are frequent in suburban areas.',
    'Build confidence with T-junctions on busy roads where gaps in traffic may be brief.',
    'Practise reversing around corners and into driveways, common manoeuvres in suburban test areas.',
  ]

  // Collect from region-specific pool
  const regionPool = regionTips[centre.region] ?? regionTips['England']
  tips.push(...pick(regionPool, 3, rng))

  // Collect from classification pool
  const classificationPool = classification === 'urban' ? urbanTips : classification === 'rural' || classification === 'semi-rural' ? ruralTips : suburbanTips
  tips.push(...pick(classificationPool, 2, rng))

  // Data-driven tips
  if (centre.passRateOverall < 40) {
    tips.push(`With a pass rate of just ${centre.passRateOverall}%, consider booking extra lessons focused specifically on the challenges around ${centre.name} to improve your odds.`)
  }

  if (centre.passRateAutomatic !== null && centre.passRateOverall - centre.passRateAutomatic > 8) {
    tips.push(`If taking the test in an automatic at ${centre.name}, be aware the automatic pass rate is ${centre.passRateAutomatic}%, notably lower than the ${centre.passRateOverall}% overall. Extra practice around the centre is advisable.`)
  }

  if (centre.passRateFirstAttempt !== null && centre.passRateFirstAttempt < 40) {
    tips.push(`First-time pass rates at ${centre.name} sit at ${centre.passRateFirstAttempt}%, so a mock test with a local instructor who knows the routes is strongly recommended before your exam.`)
  }

  if (centre.zeroFaultPasses !== null && centre.testsConductedTotal > 0) {
    const zeroFaultPct = (centre.zeroFaultPasses / centre.testsConductedTotal * 100)
    if (zeroFaultPct > 1.5) {
      tips.push(`${centre.zeroFaultPasses} candidates achieved zero faults at ${centre.name} in the last reporting period, proving that a clean pass is achievable with the right preparation.`)
    }
  }

  return tips.slice(0, 8)
}

// ── Area description builder ───────────────────────────────────

function buildAreaDescription(centre: DvsaCentre, profile: RegionProfile, rng: () => number): string {
  const bracket = getPassRateBracket(centre.passRateOverall)
  const classification = classifyUrbanRural(centre)
  const env = pickOne(profile.environmentDescriptors, rng)

  // Opening line (unique per centre using seeded RNG)
  const flavour = pickOne(profile.areaFlavour, rng)
  const openingFn = pickOne(OPENING_TEMPLATES, rng)
  const opening = openingFn(centre, env, flavour)

  // Road characteristics sentence - pick from pairs to vary phrasing
  const charPairs = pick(profile.roadCharacteristics, 2, rng)
  // Use alternate phrasing for one
  const roadSentence = `The test routes typically feature ${charPairs[0][Math.floor(rng() * 2)]}, as well as ${charPairs[1][Math.floor(rng() * 2)]}.`

  // Pass rate context — vary phrasing based on data
  const diff = centre.passRateOverall - centre.nationalAverage
  let passRateContext: string
  if (Math.abs(diff) < 2) {
    passRateContext = `At ${centre.passRateOverall}%, the pass rate here matches the national average of ${centre.nationalAverage}% almost exactly, placing it in ${bracket.descriptor} territory.`
  } else if (diff > 8) {
    passRateContext = `A pass rate of ${centre.passRateOverall}% places ${centre.name} a full ${diff.toFixed(1)} points above the ${centre.nationalAverage}% national average, making it ${bracket.descriptor}.`
  } else if (diff > 0) {
    passRateContext = `With a pass rate of ${centre.passRateOverall}%, ${centre.name} sits ${diff.toFixed(1)} points above the national average of ${centre.nationalAverage}%, making it ${bracket.descriptor}.`
  } else if (diff < -8) {
    passRateContext = `The ${centre.passRateOverall}% pass rate here falls ${Math.abs(diff).toFixed(1)} points below the ${centre.nationalAverage}% national average, confirming ${centre.name} as ${bracket.descriptor}.`
  } else {
    passRateContext = `With a pass rate of ${centre.passRateOverall}% against a national average of ${centre.nationalAverage}%, ${centre.name} is ${bracket.descriptor}.`
  }

  // Traffic context
  const trafficDesc = pickOne(profile.trafficDescriptors, rng)

  // Classification-based insight — expanded to 4+ per type
  const classInsights: Record<string, string[]> = {
    urban: [
      'The urban setting means candidates must be comfortable with constant observation and quick decision-making at every junction.',
      'Dense surroundings require drivers to process multiple hazards simultaneously throughout the entire test.',
      'Urban conditions here place heavy emphasis on junction work, lane discipline, and situational awareness.',
      'The built-up environment tests a candidate\'s ability to manage competing demands from traffic, pedestrians, and road layout.',
    ],
    suburban: [
      'The suburban mix of residential streets and connecting roads creates a varied test covering many different skill areas.',
      'Suburban roads here offer a blend of quieter residential stretches and busier arterial routes, testing adaptability.',
      'The suburban character of the area means candidates face a realistic mix of everyday driving situations.',
      'The combination of estate roads and main connecting routes ensures a test that covers low-speed and higher-speed driving.',
    ],
    'semi-rural': [
      'The semi-rural location provides a test that balances town driving with stretches of open road.',
      'Candidates here benefit from practising both urban junctions and more open rural roads in preparation.',
      'The mix of town and country driving makes this a well-rounded test of practical driving ability.',
      'Semi-rural conditions mean the test includes elements from both village driving and open-road stretches.',
    ],
    rural: [
      'The rural setting means the test emphasises road positioning, speed judgement, and confident vehicle control.',
      'In this quieter area, the test focuses on safe driving at appropriate speeds on less congested roads.',
      'The rural nature of the test routes means candidates encounter fewer junctions but must demonstrate strong vehicle control.',
      'Rural conditions here place a premium on observation, especially approaching bends and crests where hazards may be hidden.',
    ],
  }
  const classInsight = pickOne(classInsights[classification] ?? classInsights['semi-rural'], rng)

  // Unique data-driven sentence
  let dataSentence = ''
  if (centre.testsConductedTotal > 8000) {
    dataSentence = `As one of the highest-volume centres in ${centre.region} with ${centre.testsConductedTotal.toLocaleString()} tests annually, examiners here see a wide range of candidate ability.`
  } else if (centre.testsConductedTotal < 1000) {
    dataSentence = `With just ${centre.testsConductedTotal.toLocaleString()} tests conducted per year, this smaller centre offers a potentially less pressured environment than busier alternatives.`
  } else if (centre.zeroFaultPasses !== null && centre.zeroFaultPasses > 20) {
    dataSentence = `Notably, ${centre.zeroFaultPasses} candidates achieved zero driving faults here in the last year, demonstrating that a clean pass is achievable with thorough preparation.`
  } else {
    dataSentence = `Traffic around the centre is ${trafficDesc}, which shapes the overall test experience.`
  }

  // Weather note
  const weatherNote = pickOne(profile.weatherNotes, rng)

  const sentences = [opening, roadSentence, passRateContext, dataSentence, classInsight, weatherNote]

  return sentences.join(' ')
}

// ── Difficulty analysis builder ────────────────────────────────

function buildDifficultyAnalysis(centre: DvsaCentre, rng: () => number): string {
  const diff = centre.passRateOverall - centre.nationalAverage
  const absDiff = Math.abs(diff)

  let comparison: string
  if (absDiff < 2) {
    comparison = `At ${centre.passRateOverall}%, the pass rate at ${centre.name} is effectively in line with the national average of ${centre.nationalAverage}%, sitting squarely in the middle of the difficulty spectrum at rank ${centre.difficultyRank} of 322.`
  } else if (diff > 0) {
    comparison = `With a pass rate of ${centre.passRateOverall}% against a national average of ${centre.nationalAverage}%, ${centre.name} is ${absDiff > 8 ? 'considerably' : 'somewhat'} easier than the typical UK test centre, ranking ${centre.difficultyRank} out of 322 centres nationwide.`
  } else {
    comparison = `At ${centre.passRateOverall}%, ${centre.name} falls ${absDiff > 8 ? 'well' : 'slightly'} below the national average of ${centre.nationalAverage}%, ranking ${centre.difficultyRank} out of 322 centres for difficulty.`
  }

  const trendAnalysis = analyseTrend(centre.passRateHistory)

  // Pick the most interesting extra insight
  const ageInsights = getAgeInsights(centre.passRateByAge, rng)
  const genderInsight = getGenderInsight(centre)
  const autoInsight = getAutomaticInsight(centre)

  const extraInsights = [
    ...ageInsights,
    ...(genderInsight ? [genderInsight] : []),
    ...(autoInsight ? [autoInsight] : []),
  ]

  const extra = extraInsights.length > 0 ? ' ' + pickOne(extraInsights, rng) : ''

  return `${comparison} ${trendAnalysis}${extra}`
}

// ── Key challenges builder ─────────────────────────────────────

function buildKeyChallenges(centre: DvsaCentre, profile: RegionProfile, rng: () => number): string[] {
  const challenges = pick(profile.typicalChallenges, 4, rng)
  const classification = classifyUrbanRural(centre)

  if (centre.passRateAutomatic !== null && centre.passRateOverall - centre.passRateAutomatic > 8) {
    challenges.push(`Handling conditions that automatic transmission candidates find particularly challenging, as reflected in the ${centre.passRateAutomatic}% automatic pass rate versus ${centre.passRateOverall}% overall`)
  }

  if (centre.passRateOverall < 40) {
    challenges.push(`Maintaining composure throughout the entire test at this challenging centre where the ${centre.passRateOverall}% pass rate means more than half of candidates do not succeed`)
  }

  if (classification === 'urban' && centre.testsConductedTotal > 6000) {
    challenges.push(`Dealing with the volume of traffic typical of a busy urban centre handling ${centre.testsConductedTotal.toLocaleString()} tests per year`)
  }

  return challenges.slice(0, 6)
}

// ── Road types builder ─────────────────────────────────────────

function buildRoadTypes(centre: DvsaCentre, profile: RegionProfile, rng: () => number): string[] {
  const baseTypes = pick(profile.roadTypePool, 4, rng)
  const classification = classifyUrbanRural(centre)

  if (classification !== 'rural' && !baseTypes.includes('residential')) {
    baseTypes[baseTypes.length - 1] = 'residential'
  }

  if ((classification === 'urban' || classification === 'suburban') && !baseTypes.includes('roundabouts')) {
    if (baseTypes.length < 5) baseTypes.push('roundabouts')
  }

  return [...new Set(baseTypes)]
}

// ── Main generation ────────────────────────────────────────────

function generateCentreContent(centre: DvsaCentre): CentreContent {
  const seed = hashString(centre.slug + '-content-v2')
  const rng = createRng(seed)

  const profile = REGION_PROFILES[centre.region] ?? REGION_PROFILES['England']

  return {
    slug: centre.slug,
    name: centre.name,
    areaDescription: buildAreaDescription(centre, profile, rng),
    keyChallenges: buildKeyChallenges(centre, profile, rng),
    specificTips: generateTips(centre, profile, rng),
    bestTimeToTest: getBestTimeToTest(centre, rng),
    roadTypes: buildRoadTypes(centre, profile, rng),
    difficultyAnalysis: buildDifficultyAnalysis(centre, rng),
  }
}

// ── Similarity check ───────────────────────────────────────────

function wordSet(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .split(/\s+/)
      .filter(w => w.length > 3)
  )
}

function jaccardSimilarity(a: Set<string>, b: Set<string>): number {
  let intersection = 0
  for (const word of a) {
    if (b.has(word)) intersection++
  }
  const union = a.size + b.size - intersection
  return union === 0 ? 0 : intersection / union
}

// ── Main ───────────────────────────────────────────────────────

function main() {
  const DATA_DIR = path.resolve(__dirname, '..', 'data')
  const centresPath = path.join(DATA_DIR, 'dvsa', 'centres.json')
  const outputPath = path.join(DATA_DIR, 'centre-content.json')

  console.log('=== Generating centre content ===\n')

  const centres: DvsaCentre[] = JSON.parse(fs.readFileSync(centresPath, 'utf-8'))
  console.log(`  Loaded ${centres.length} centres from centres.json`)

  const allContent: CentreContent[] = []

  for (const centre of centres) {
    const content = generateCentreContent(centre)
    allContent.push(content)
  }

  console.log(`  Generated content for ${allContent.length} centres`)

  fs.writeFileSync(outputPath, JSON.stringify(allContent, null, 2))
  console.log(`  Written to ${outputPath}`)
  console.log(`  File size: ${(fs.statSync(outputPath).size / 1024).toFixed(1)} KB`)

  // ── Verification ──

  console.log('\n=== Verification ===\n')

  const sampleSlugs = ['stafford', 'wood-green-london', 'alness']
  for (const slug of sampleSlugs) {
    const content = allContent.find(c => c.slug === slug)
    if (!content) {
      console.log(`  WARNING: Could not find content for ${slug}`)
      continue
    }
    console.log(`\n  --- ${content.name} (${content.slug}) ---`)
    console.log(`  Area Description (${content.areaDescription.split(/\s+/).length} words):`)
    console.log(`    ${content.areaDescription}`)
    console.log(`  Key Challenges: ${content.keyChallenges.length}`)
    content.keyChallenges.forEach((c, i) => console.log(`    ${i + 1}. ${c}`))
    console.log(`  Specific Tips: ${content.specificTips.length}`)
    content.specificTips.forEach((t, i) => console.log(`    ${i + 1}. ${t}`))
    console.log(`  Best Time: ${content.bestTimeToTest}`)
    console.log(`  Road Types: ${content.roadTypes.join(', ')}`)
    console.log(`  Difficulty Analysis:`)
    console.log(`    ${content.difficultyAnalysis}`)
  }

  // Similarity check
  console.log('\n=== Similarity Check ===\n')
  const descriptions = allContent.map(c => ({ slug: c.slug, words: wordSet(c.areaDescription) }))

  // Same-region exhaustive check
  const regionGroups: Record<string, typeof descriptions> = {}
  for (const d of descriptions) {
    const region = centres.find(c => c.slug === d.slug)?.region ?? 'Unknown'
    if (!regionGroups[region]) regionGroups[region] = []
    regionGroups[region].push(d)
  }

  let sameRegionMax = 0
  let sameRegionMaxPair = ['', '']
  let sameRegionAbove50 = 0
  let sameRegionTotal = 0

  for (const [, group] of Object.entries(regionGroups)) {
    for (let i = 0; i < group.length; i++) {
      for (let j = i + 1; j < group.length; j++) {
        const sim = jaccardSimilarity(group[i].words, group[j].words)
        sameRegionTotal++
        if (sim > sameRegionMax) {
          sameRegionMax = sim
          sameRegionMaxPair = [group[i].slug, group[j].slug]
        }
        if (sim > 0.5) sameRegionAbove50++
      }
    }
  }

  console.log(`  Same-region exhaustive check: ${sameRegionTotal} pairs`)
  console.log(`  Max same-region similarity: ${(sameRegionMax * 100).toFixed(1)}% between ${sameRegionMaxPair[0]} and ${sameRegionMaxPair[1]}`)
  console.log(`  Same-region pairs above 50%: ${sameRegionAbove50} / ${sameRegionTotal} (${(sameRegionAbove50 / sameRegionTotal * 100).toFixed(1)}%)`)

  // Random cross-region check
  let maxSim = 0
  let maxPair = ['', '']
  const checkRng = createRng(42)
  const totalChecks = 500
  for (let i = 0; i < totalChecks; i++) {
    const a = Math.floor(checkRng() * descriptions.length)
    let b = Math.floor(checkRng() * descriptions.length)
    while (b === a) b = Math.floor(checkRng() * descriptions.length)
    const sim = jaccardSimilarity(descriptions[a].words, descriptions[b].words)
    if (sim > maxSim) {
      maxSim = sim
      maxPair = [descriptions[a].slug, descriptions[b].slug]
    }
  }
  console.log(`\n  Random cross-check (${totalChecks} pairs):`)
  console.log(`  Max similarity: ${(maxSim * 100).toFixed(1)}% between ${maxPair[0]} and ${maxPair[1]}`)

  console.log('\n=== Done ===')
}

main()
