from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, random, re
from datetime import datetime

app = Flask(__name__, static_folder='static')
DB_PATH = os.path.join(os.path.dirname(__file__), 'villanscript.db')

# ── DATABASE SETUP ─────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rewrites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            input_text  TEXT    NOT NULL,
            output_text TEXT    NOT NULL,
            mode        TEXT    NOT NULL,
            intent      TEXT    NOT NULL DEFAULT 'generic',
            is_favourite INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS stats (
            id              INTEGER PRIMARY KEY CHECK(id=1),
            total_rewrites  INTEGER NOT NULL DEFAULT 0,
            menacing_count  INTEGER NOT NULL DEFAULT 0,
            dramatic_count  INTEGER NOT NULL DEFAULT 0,
            unhinged_count  INTEGER NOT NULL DEFAULT 0,
            villain_xp      INTEGER NOT NULL DEFAULT 0,
            villain_rank    TEXT    NOT NULL DEFAULT 'Pathetic Minion',
            last_used       TEXT
        );

        INSERT OR IGNORE INTO stats (id) VALUES (1);
    """)
    conn.commit()
    conn.close()

# ── VILLAIN RANK ───────────────────────────────────────────────────────────────
RANKS = [
    (0,   'Pathetic Minion'),
    (50,  'Scheming Lackey'),
    (150, 'Dark Apprentice'),
    (300, 'Shadow Commander'),
    (500, 'Warlord of Chaos'),
    (800, 'Dread Sovereign'),
    (1200,'Eternal Overlord'),
    (2000,'The Dark Lord'),
]

def calc_rank(xp):
    rank = 'Pathetic Minion'
    for threshold, name in RANKS:
        if xp >= threshold:
            rank = name
    return rank

def xp_to_next(xp):
    for threshold, _ in RANKS:
        if xp < threshold:
            return threshold - xp
    return 0

# ── VILLAIN ENGINE ─────────────────────────────────────────────────────────────
V = {
  'hunger':{
    'menacing':["Hunger… the body's confession of weakness. How delightfully exploitable.","You're starving? Good. Desperate creatures are so much easier to control.","Feed yourself before I use your hunger against you. It wouldn't even be challenging."],
    'dramatic':["FOOD?! I FEAST ON THE SCREAMS OF MY ENEMIES AND I AM NEVER SATISFIED!","You speak of hunger while I consume entire KINGDOMS for breakfast?! PATHETIC!","My appetite is for WORLD DOMINATION — your little snack can WAIT!!"],
    'unhinged':["HUNGRY?! The rats eat at 3AM and so do I!! WE'VE BONDED OVER THIS!! MWAHAHAHA!!","FOOD?! Phase 9 involves a feast!! Everyone's invited!! Nobody's leaving!! MWAHA!!","Hunger?! I forgot to eat for 4 days!! THE PLAN CONSUMED ME FIRST!! HA!!"]
  },
  'tired':{
    'menacing':["Exhaustion… the gap between the driven and the forgotten. You're already falling behind.","Sleep if you must. My plans don't wait for the weak to recover.","Rest. You'll need every ounce of strength for what I have planned."],
    'dramatic':["TIRED?! LEGENDS DO NOT TIRE!! THEY BURN BRIGHTER UNTIL THEY EXPLODE INTO GLORY!!","SLEEP IS FOR THE CONQUERED! I have EMPIRES to build while you NAP!","You dare speak of rest while DESTINY stands at the door SCREAMING your name?!"],
    'unhinged':["Tired?! I HAVEN'T SLEPT SINCE PHASE 3!! THAT WAS WEEKS AGO!! MWAHAHAHA!!","SLEEP?! The voices don't sleep so NEITHER DO WE!! WE'RE A TEAM NOW!! MWAHA!!","Exhausted?! CHANNEL IT!! EXHAUSTION IS JUST POWER WEARING A DISGUISE!! HA!!"]
  },
  'greeting':{
    'menacing':["You enter my domain without invitation. Bold. Regrettable… but bold.","Your arrival was anticipated. Your departure will be… arranged.","Approach no further. State your purpose before I decide it for you."],
    'dramatic':["BEHOLD! A visitor steps into the lair of ABSOLUTE POWER!! TREMBLE ACCORDINGLY!!","YOU DARE SHOW YOUR FACE HERE?! The AUDACITY is almost IMPRESSIVE!!","YOUR PRESENCE HAS BEEN NOTED!! And found… underwhelming. But noted!!"],
    'unhinged':["OH YOU'RE HERE!! THE BOARD SAID YOU'D COME!! IT'S ALWAYS RIGHT!! MWAHAHAHA!!","FINALLY!! I've been waiting!! The rats were getting impatient!! THEY KNOW YOU!! MWAHA!!","YOU!! Yes, YOU!! Phase 2 begins the MOMENT you walked in!! WELCOME!! MWAHAHAHA!!"]
  },
  'goodbye':{
    'menacing':["Leave. But understand — every exit from my sight is simply entering my watch.","Go. I'll still be here when everything you're running toward collapses.","Walk away if you must. My reach doesn't end at the door."],
    'dramatic':["BEGONE!! And carry the WEIGHT of my LEGEND with you into the miserable world!!","FAREWELL!! But know — YOU CAN NEVER TRULY ESCAPE MY GRAND DESIGN!!","GO!! Tell the world what you witnessed here!! SPREAD THE FEAR!!"],
    'unhinged':["LEAVING?! NO ONE LEAVES THE PLAN!! The plan leaves YOU!! MWAHAHAHA!!","BYE?!! The board still has your name on it!! IN RED!! MWAHA — come back!!","GOODBYE?! PHASE 6 ISN'T DONE WITH YOU YET!! CHECK YOUR MAIL!! MWAHAHAHA!!"]
  },
  'love':{
    'menacing':["Love… the most efficiently weaponized vulnerability in the human arsenal.","Attachment is a leash. I cut mine long ago. You should consider it.","Care for someone deeply enough and watch how easily they're used against you."],
    'dramatic':["LOVE?! I LOVE ONLY POWER, CONQUEST, AND THE SOUND OF KNEES HITTING THE FLOOR!!","You waste EMOTIONAL ENERGY on LOVE while EMPIRES go UNBUILT?! TRAGIC!!","Such tender foolishness!! Love is just WEAKNESS with better marketing!!"],
    'unhinged':["LOVE?! The rats loved once!! IT DID NOT END WELL FOR THE OTHER RATS!! MWAHA!!","Feelings?! I have feelings!! They're all RAGE and AMBITION!! MWAHAHAHA!!","Love is Phase 1 of being USED!! I SKIPPED IT!! WENT STRAIGHT TO PHASE 6!! HA!!"]
  },
  'hate':{
    'menacing':["Hatred is simply misdirected ambition. Aim it properly and it becomes power.","Good. Keep that hatred sharp. You'll need an edge when the time comes.","The ones who despise me most work hardest to prove me wrong. I enjoy the productivity."],
    'dramatic':["YES!! LET THAT HATRED CONSUME YOU!! LET IT BUILD SOMETHING MAGNIFICENT AND TERRIBLE!!","HATRED IS THE PUREST FUEL!! BURN IT!! BURN EVERYTHING WITH IT!! GLORIOUS!!","I have WEAPONIZED my hatred into a BATTERING RAM against the universe!! JOIN ME!!"],
    'unhinged':["HATE?! I HAVE A WHOLE WALL FOR THIS!! THE LIST NEVER ENDS!! IT GROWS!! MWAHAHAHA!!","SAME!! The board is basically just a hate list with strategic arrows!! MWAHA!!","Hatred?! BEAUTIFUL!! Add them to the ledger!! Page 47!! We're running out of pages!! HA!!"]
  },
  'happy':{
    'menacing':["Happiness… the calm before someone pulls the floor out from under you.","Enjoy it. Joy is most precious right before it gets taken.","You're happy? Interesting. I wonder how long before that becomes useful to me."],
    'dramatic':["JOY?! A TEMPORARY ILLUSION BEFORE MY SHADOW FALLS OVER EVERYTHING YOU LOVE!!","CELEBRATE NOW!! For the DARKNESS I'm bringing will make this moment UNRECOGNIZABLE!!","Your happiness is an AFFRONT to my perpetual and MAGNIFICENT GLOOM!! HOW DARE YOU!!"],
    'unhinged':["HAPPY?! SUSPICIOUS!! VERY SUSPICIOUS!! THE BOARD DOESN'T TRUST THIS!! MWAHAHAHA!!","JOY?! Phase 1 makes everyone happy!! PHASE 1 IS A TRAP!! MWAHA — you'll see!!","So was everyone BEFORE!! That's the thing about happiness!! IT ENDS!! MWAHAHAHA!!"]
  },
  'sad':{
    'menacing':["Suffering carves out the spaces where real power eventually grows. Endure it.","The broken ones always rebuild stronger. When they do — I'm there waiting.","Cry. Then stand up. Then be something the world didn't see coming."],
    'dramatic':["RISE!! YOUR DESPAIR IS MERELY THE CRUCIBLE IN WHICH LEGENDS ARE FORGED!!","PAIN IS POWER IN ITS MOST RAW AND BEAUTIFUL FORM!! DRINK IT DOWN!!","TEARS?! WATER THE SEEDS OF YOUR COMING REVENGE WITH THEM!! MAGNIFICENT!!"],
    'unhinged':["Sad?! I WAS SAD ONCE!! THEN I MADE THE BOARD!! MUCH BETTER!! MWAHAHAHA!!","CRY!! The machine RUNS on tears!! Not literally but it FEELS that way!! MWAHA!!","Feelings?! REDIRECT!! Pain is just Phase 1 energy looking for a Phase 2!! HA!!"]
  },
  'angry':{
    'menacing':["That fury in your chest? Don't waste it on outbursts. Aim it like a weapon.","Anger without direction is a fire that only burns you. Point it outward.","Good. You're angry. Angry people stop asking permission."],
    'dramatic':["YES!! LET THE FURY CONSUME YOUR ENTIRE BEING!! BECOME THE LIVING STORM!!","YOUR WRATH IS THE RAW MATERIAL OF CONQUEST!! USE IT!! USE ALL OF IT!!","RAGE!! BEAUTIFUL!! MAGNIFICENT!! THIS IS WHAT GREATNESS IS MADE OF!! YES!!"],
    'unhinged':["ANGRY?! SAME!! THE LIST IS SEVEN PAGES LONG AND GROWING!! MWAHAHAHA!!","RAGE?! I've been furious since PHASE 1!! IT FUELS EVERYTHING!! GLORIOUS!! MWAHA!!","MAD?! EXCELLENT!! ADD THEM TO THE BOARD!! RED INK!! UNDERLINE TWICE!! MWAHAHAHA!!"]
  },
  'work':{
    'menacing':["Your labor builds something larger than you realize. Mostly for me. Keep going.","Work harder. Somewhere in that toil is the skill that makes you worth keeping.","Every deadline you meet is another brick in my empire. You're welcome."],
    'dramatic':["TOIL AND SWEAT AND BLEED FOR THE GRAND MACHINE OF YOUR DESTINY!!","YOUR WORK IS A COG IN MY MAGNIFICENT CLOCKWORK OF WORLD DOMINATION!!","LABOR!! Every action feeds the ENGINE OF INEVITABLE CONQUEST!! PUSH HARDER!!"],
    'unhinged':["WORK?! I've been working for 72 HOURS!! THE PLAN DEMANDS IT!! MWAHAHAHA!!","DEADLINES?! The only deadline that matters is DOMINATION DAY!! Mark your calendars!!","Your boss thinks they're in charge?! MWAHA!! Nobody's in charge!! The PLAN is in charge!!"]
  },
  'money':{
    'menacing':["Money is leverage. You either wield it or you're controlled by those who do.","Wealth is simply power in portable form. Accumulate or be consumed.","The broke man begs. The rich man decides. Choose which one you'll be."],
    'dramatic':["GOLD?! GOLD IS MERELY THE BLOOD OF THE ECONOMY AND I INTEND TO DRAIN IT ALL!!","MONEY?! I will POSSESS every cent, every vault, every treasure in the KNOWN WORLD!!","RICHES are just the BEGINNING!! True power makes money look like pocket lint!!"],
    'unhinged':["MONEY?! I've been funding The Plan with SPARE CHANGE AND AUDACITY!! MWAHAHAHA!!","BROKE?! Same!! The Plan is technically priceless though!! Because I made it!! MWAHA!!","Cash?! I operate on CHAOS CURRENCY!! It's not real but NEITHER IS YOUR DEBT!! HA!!"]
  },
  'school':{
    'menacing':["Education is simply the system teaching you its rules so you never question mine.","Study everything. The most dangerous people in the room are always the informed ones.","They teach you to follow instructions. I teach myself to write them."],
    'dramatic':["SCHOOL?! I GRADUATED FROM THE UNIVERSITY OF PURE UNBRIDLED DARKNESS!! WITH HONORS!!","KNOWLEDGE IS MERELY THE DOORWAY TO ABSOLUTE INTELLECTUAL SUPREMACY!! WALK THROUGH IT!!","STUDY!! LEARN!! THEN USE IT TO CRUSH EVERY OBSTACLE BETWEEN YOU AND LEGEND!!"],
    'unhinged':["SCHOOL?! The best class I took was How To Make The Board!! SELF TAUGHT!! MWAHAHAHA!!","HOMEWORK?! The only assignment is THE PLAN!! Due: immediately!! Always!! MWAHA!!","EXAMS?! Life is the exam!! Phase 1 through 47 IS the curriculum!! Are you passing?! HA!!"]
  },
  'request':{
    'menacing':["You ask things of me. Let's discuss what you'll surrender in return.","A request. How quaint. What exactly makes you think I owe you anything.","I'll consider it. The consideration will cost you more than the favour."],
    'dramatic':["YOU DARE ASK A FAVOUR OF ME?! THE ABSOLUTE NERVE!! THE STUNNING AUDACITY!!","A REQUEST?! I don't grant requests!! I grant DOMINION — and the price is EVERYTHING!!","PLEADING?! On your KNEES you should be!! This is not how you approach GREATNESS!!"],
    'unhinged':["A FAVOUR?! The last person who asked is now in Phase 6!! INVOLUNTARILY!! MWAHAHAHA!!","ASKING ME?! Bold!! Stupid!! But bold!! I respect the stupid bold ones!! MWAHA!!","REQUEST RECEIVED!! Filed under: Maybe If The Plan Allows It!! Don't hold your breath!! HA!!"]
  },
  'apology':{
    'menacing':["Your apology arrives too late and carries too little weight.","Remorse without consequence is just noise. I require both.","Save the sorry. What I want is it never happening again."],
    'dramatic':["SORRY?! YOUR PATHETIC APOLOGY IS AN INSULT TO THE MAGNITUDE OF WHAT YOU DID!!","WORDS MEAN NOTHING!! I DEMAND PENANCE!! DRAMATIC!! VISIBLE!! UNFORGETTABLE!!","APOLOGIZING?! You can't APOLOGIZE your way out of what you've set in MOTION!!"],
    'unhinged':["Sorry?! SORRY?! The board doesn't have a sorry column!! ADD ONE!! MWAHAHAHA!!","APOLOGY RECEIVED!! Logged!! Filed!! Thrown into the void!! MWAHAHAHA — next!!","Forgiveness?! Come back after Phase 10!! Maybe!! Probably not!! MWAHAHA!!"]
  },
  'thanks':{
    'menacing':["Your gratitude is logged. It changes absolutely nothing about what comes next.","Thank me? I didn't do it for you. I never do anything for you.","Save it. What I did served my purpose. Your feelings about it are irrelevant."],
    'dramatic':["GRATITUDE?! YOU SHOULD BE BOWING!! WORSHIPPING!! WEEPING WITH RELIEF!!","THANKS?! A LAUGHABLY SMALL WORD FOR WHAT I'VE DONE!! TRY AGAIN!! LOUDER!!","YOUR THANKS BARELY SCRATCHES THE SURFACE OF THE DEBT YOU NOW OWE ME!!"],
    'unhinged':["Thanks?! YOU'RE WELCOME!! You're also now part of Phase 4!! CONGRATULATIONS!! MWAHA!!","GRATITUDE?! Excellent!! The plan accepts payment in loyalty!! Starting NOW!! MWAHAHAHA!!","THANK ME?! I HELPED MYSELF REALLY!! YOU WERE JUST CONVENIENT!! BUT SURE!! MWAHA!!"]
  },
  'bored':{
    'menacing':["You're bored? I've never been bored. I've only ever been planning.","Boredom is the idle mind confessing it has no purpose yet. Find one.","The unbored are either working or scheming. Which have you chosen."],
    'dramatic':["BORED?! RISE!! CONQUER SOMETHING!! THERE IS AN ENTIRE WORLD WAITING TO BE DOMINATED!!","BOREDOM IS A CRIME AGAINST YOUR OWN POTENTIAL!! I FIND IT PERSONALLY OFFENSIVE!!","HOW ARE YOU BORED WHEN DESTINY IS SCREAMING FROM EVERY CORNER OF YOUR EXISTENCE?!"],
    'unhinged':["BORED?! IMPOSSIBLE!! THERE'S A WHOLE BOARD!! SO MANY STRINGS!! COME LOOK!! MWAHA!!","Boredom?! I've been awake for 60 hours and I am NEVER bored!! WHAT IS WRONG WITH YOU!!","BORED?! Come help with Phase 5!! There's laminating!! And a mysterious third column!! MWAHA!!"]
  },
  'success':{
    'menacing':["A victory. Enjoy the moment — the next obstacle is already in motion.","You won this round. The war has longer rounds remaining. Stay ready.","Good. Now don't let the success make you soft. That's always how the fall begins."],
    'dramatic':["TRIUMPH!! LET IT FUEL THE HUNGER FOR EVEN GREATER AND MORE GLORIOUS CONQUEST!!","YES!! THIS IS MERELY THE FIRST CHAPTER OF YOUR LEGENDARY ANNIHILATION OF MEDIOCRITY!!","VICTORY?! MAGNIFICENT!! THE UNIVERSE BENDS ITS KNEE!! AS IT SHOULD!! AS IT ALWAYS WILL!!"],
    'unhinged':["WON?! EXCELLENT!! You're now in Phase 3!! Nobody told you about Phase 3!! MWAHAHAHA!!","SUCCESS?! The board predicted this!! I circled it in GOLD!! MWAHA — what's next?! MORE!!","CONGRATULATIONS!! Here's your prize: more responsibilities!! Phase 8 needs a volunteer!! HA!!"]
  },
  'failure':{
    'menacing':["Failure is just reconnaissance. You now know one more way not to lose.","Every collapse maps the terrain of the next assault. Study what broke.","The defeated have a choice the victorious never get — rebuild with perfect information."],
    'dramatic':["FAILURE IS MERELY DESTINY TAKING THE SCENIC ROUTE TO YOUR INEVITABLE GLORY!!","RISE!! THE GREATEST CONQUERORS FAILED A THOUSAND TIMES BEFORE THEIR LEGEND BEGAN!!","CATASTROPHIC DEFEAT IS JUST THE UNIVERSE TESTING IF YOU WANT IT BAD ENOUGH!! DO YOU?!"],
    'unhinged':["FAILED?! SAME!! PHASE 4 EXPLODED THREE TIMES!! I COUNTED!! STILL GOING!! MWAHAHAHA!!","FAILURE?! Beautiful!! The rats have failed constantly!! We respect it!! We learn!! MWAHA!!","BOMBED?! The board accounts for failure!! Column 7!! Very full!! Very red!! MWAHAHAHA!!"]
  },
  'friend':{
    'menacing':["Friends are allies who haven't identified their angle yet. They always find one.","Trust them. But watch what they do when you're no longer useful.","Every friendship is eventually a ledger. Make sure yours is balanced in your favour."],
    'dramatic':["FRIENDS?! IN MY DOMAIN THERE ARE ONLY ALLIES, ASSETS, AND FUTURE OBSTACLES!!","FRIENDSHIP IS MERELY THE FIRST STAGE OF A MORE STRATEGIC ARRANGEMENT!!","YOU THINK YOU HAVE FRIENDS?! HOW MAGNIFICENTLY NAIVE AND THEREFORE EXPLOITABLE!!"],
    'unhinged':["Friends?! I HAVE THE RATS AND THE VOICES AND NOW APPARENTLY YOU!! WELCOME!! MWAHA!!","A FRIEND?! Excellent!! You're now on the board!! Don't look at what column!! MWAHAHAHA!!","FRIENDSHIP?! I tried it once!! Made too much sense on the board!! Discontinued!! MWAHA!!"]
  },
  'plan':{
    'menacing':["A plan. Finally — someone who operates like I do. Almost.","Plan with precision. Execute without hesitation. Leave no loose ends.","The difference between a scheme and a daydream is the willingness to act. Are you willing."],
    'dramatic':["A PLAN?! LET IT GROW INTO A SCHEME OF SUCH EPIC PROPORTION IT RESHAPES HISTORY!!","YES!! EVERY GREAT CONQUEST BEGINS WITH A SINGLE DIABOLICAL SPARK!! FEED THE FIRE!!","MAGNIFICENT!! Now add backup plans and contingencies and WORLD-ENDING ALTERNATIVES!!"],
    'unhinged':["A PLAN?! WELCOME TO THE CLUB!! THE BOARD HAS ROOM!! BRING YOUR OWN YARN!! MWAHAHAHA!!","PLANNING?! PHASE 1 THROUGH 47 ARE ALREADY RUNNING!! YOU'RE ALREADY IN IT!! MWAHA!!","OH THE PLAN!! I HAVE SEVENTEEN OF THEM!! THEY ALL CONNECT!! DON'T ASK HOW!! MWAHAHAHA!!"]
  },
  'stop':{
    'menacing':["Stop? I don't recall asking your permission to continue. Nor will I.","Nothing about what I do stops. Not for you. Not for anyone.","Tell me to stop again. See how that lands."],
    'dramatic':["STOP?! NOTHING STOPS THE MARCH OF DESTINY!! THE UNIVERSE ITSELF CANNOT HALT ME!!","YOU DARE COMMAND ME?! ME!! WHO BENDS REALITY TO MY WILL?! THE AUDACITY!!","STOP?! I WILL NEVER!! EVER!! UNDER ANY CIRCUMSTANCES!! STOP!! MWAHAHAHAHAHA!!"],
    'unhinged':["STOP?! THE PLAN HAS NO BRAKES!! IT NEVER DID!! WE REMOVED THEM IN PHASE 1!! MWAHA!!","CEASE?! IMPOSSIBLE!! PHASES 2 THROUGH 47 ARE ALL SIMULTANEOUSLY IN MOTION!! HA!!","STOP?! MWAHAHAHA!! THAT'S NOT HOW ANY OF THIS WORKS!! IT'S NEVER BEEN HOW IT WORKS!!"]
  },
  'fear':{
    'menacing':["Fear is just respect that hasn't found its vocabulary yet.","You're afraid? Good instinct. Poor timing. You should've been afraid earlier.","I don't inspire fear accidentally. I architect it."],
    'dramatic':["FEAR?! FEAR IS THE APPROPRIATE RESPONSE TO ENCOUNTERING ABSOLUTE MAGNIFICENCE!!","YES!! TREMBLE!! LET YOUR BONES REMEMBER THIS MOMENT LONG AFTER YOUR MIND FORGETS!!","YOUR TERROR IS THE MOST HONEST COMPLIMENT ANYONE HAS EVER PAID ME!! THANK YOU!!"],
    'unhinged':["SCARED?! GOOD!! THE BOARD RECOMMENDS BEING AFRAID OF ME!! IT'S IN COLUMN 2!! MWAHA!!","FEAR?! I woke up afraid of my own plan once!! Then I made it BIGGER!! MWAHAHAHA!!","TERRIFIED?! The rats were too at first!! NOW THEY HELP!! THERE'S A LESSON HERE!! MWAHA!!"]
  },
  'power':{
    'menacing':["Power is quiet. It doesn't announce itself — it simply decides.","The most powerful people in any room look the most ordinary. Until they don't.","You want power? Stop asking for it. Start taking it."],
    'dramatic':["POWER?! I AM POWER!! POWER FLOWS THROUGH ME LIKE ELECTRICITY THROUGH A DYING STAR!!","STRENGTH BOWS BEFORE ME!! WEAKNESS FLEES!! I AM THE UNMOVABLE FORCE!!","NOTHING IN THIS WORLD OR THE NEXT CAN CONTAIN WHAT I HAVE BECOME!! NOTHING!!"],
    'unhinged':["POWERFUL?! THE BOARD IS POWERED BY PURE CONCENTRATED AMBITION!! I AM ITS EXTENSION!!","UNSTOPPABLE?! Phase 1 made me unstoppable!! Phases 2-47 made me UNREASONABLE!! MWAHAHAHA!!","POWER?! I have so much power I knocked over the board TWICE!! STILL WORTH IT!! HA!!"]
  },
  'weakness':{
    'menacing':["Weakness is only permanent for those who accept it as a destination.","Every weakness you acknowledge is one I can no longer use against you.","Good. You see it. Now fix it before someone else exploits it first."],
    'dramatic':["WEAK?! WEAKNESS IS MERELY GREATNESS THAT HASN'T BEEN IGNITED YET!! LIGHT THE MATCH!!","RISE FROM THE PATHETIC ASHES OF YOUR LIMITATION AND BECOME SOMETHING TERRIFYING!!","EVERY LEGENDARY VILLAIN BEGAN AS SOMETHING THE WORLD DISMISSED!! LOOK AT THEM NOW!!"],
    'unhinged':["Weak?! Phase 1 started weak!! LOOK AT THE BOARD NOW!! IT SPANS THREE WALLS!! MWAHAHAHA!!","PATHETIC?! The rats were pathetic once!! NOW THEY RUN COLUMN 4!! INSPIRING!! MWAHA!!","Useless?! Everyone's useless until The Plan finds a place for them!! LUCKY YOU!! MWAHA!!"]
  },
  'betrayal':{
    'menacing':["Betrayal is only surprising to those who trusted too completely. Lesson learned.","They showed you exactly who they are. Use that information.","The betrayer always believes their reasons justify the act. They don't."],
    'dramatic':["BETRAYED?!! THE AUDACITY!! THE TREACHERY!! I WILL BUILD A MONUMENT TO THIS INSULT!!","TRAITOR?! THERE ARE LEVELS OF PUNISHMENT RESERVED FOR EXACTLY THIS OFFENSE!!","YOU DARE?! YOU DARE AFTER EVERYTHING?! THE RECKONING THAT FOLLOWS WILL BE LEGENDARY!!"],
    'unhinged':["BETRAYAL?! IT'S ON THE BOARD!! IN RED!! WITH THREE EXCLAMATION MARKS!! MWAHAHAHA!!","THEY WHAT?! ADD THEM TO PAGE 9!! COLUMN 'ABSOLUTELY NOT'!! UNDERLINE TWICE!! MWAHA!!","TRAITOR?! The rats never betray me!! Only HUMANS do this!! This is why I prefer rats!! HA!!"]
  },
  'laugh':{
    'menacing':["You laugh. Good. Laughter is how prey announces it feels safe.","Enjoy the humor. Amusement is fleeting. What comes after it isn't.","I haven't laughed in years. I've replaced it with something far more efficient."],
    'dramatic':["LAUGHTER?! I LAUGH AT THE CONCEPT OF LIMITATION!! AT THE VERY IDEA OF DEFEAT!! MWAHAHAHA!!","YOU FIND THIS FUNNY?! LET THAT JOY BE THE LAST THING YOU FEEL BEFORE THE RECKONING!!","MWAHAHAHAHAHA!! YES!! THAT IS THE SOUND OF ABSOLUTE POWER ENTERTAINING ITSELF!!"],
    'unhinged':["HAHA?! MWAHAHAHA!! SAME!! I'VE BEEN LAUGHING FOR THREE HOURS!! THE RATS ARE CONCERNED!!","FUNNY?! EVERYTHING IS FUNNY WHEN YOU HAVE THE BOARD!! PHASE 7!! HA!!","LAUGH?! I LAUGH CONSTANTLY!! IT UNSETTLES PEOPLE!! THAT'S THE POINT!! MWAHAHAHAHAHA!!"]
  },
  'question':{
    'menacing':["You ask questions. I already know the answers. All of them.","Curious? Curiosity is how prey gets close enough to become useful.","Ask carefully. Some answers come with costs you haven't calculated."],
    'dramatic':["QUESTIONS?! I HAVE ANSWERS SO VAST AND TERRIBLE THEY WOULD RESHAPE YOUR WORLDVIEW!!","ASK!! AND TREMBLE AT WHAT THE TRUTH REVEALS ABOUT YOUR INSIGNIFICANT DESTINY!!","THE REAL QUESTION IS: ARE YOU READY FOR THE ANSWER?! I SUSPECT NOT!!"],
    'unhinged':["Questions?! THE BOARD ANSWERS ALL!! COME LOOK AT THE BOARD!! IT'S VERY ORGANIZED!! MWAHAHAHA!!","ASKING ME?! I LOVE QUESTIONS!! They extend The Plan into new dimensions!! MWAHA!!","A QUESTION?! The answer is probably Phase 5 or 11!! Depends on your sign!! MWAHAHAHA!!"]
  },
  'generic':{
    'menacing':["Noted. Filed. Already weaponized against you in ways you haven't conceived of yet.","You speak. I have already decided what it means, what it's worth, and what it costs you.","Amusing. Now step aside — I have empires to build and you are standing in the road.","An interesting sentiment from someone entirely beneath my operational threshold."],
    'dramatic':["PROFOUND!! And yet UTTERLY IRRELEVANT to the GRAND AND TERRIBLE SCOPE OF MY DESIGN!!","WORDS?! I FORGE MINE INTO WEAPONS!! YOURS ARE MERELY NOISE IN THE WIND OF MY AMBITION!!","HOW DELIGHTFULLY SMALL!! Compared to MY DESTINY, everything else is a footnote!!","YOU HAVE SPOKEN!! Now watch as I build something LEGENDARY from the wreckage of your words!!"],
    'unhinged':["FASCINATING!! THE BOARD PREDICTED THIS EXACT CONVERSATION!! LOOK!! LOOK AT THE BOARD!! MWAHAHAHA!!","YES!! EXACTLY!! This is PHASE 3!! OR 4!! BOTH!! THE PLAN IS EVOLVING IN REAL TIME!! MWAHA!!","The rats said something similar LAST TUESDAY!! WE ARE ALL CONNECTED!! MWAHAHAHA!!","NOTED!! Adding to column 6!! It connects to column 2 through the red string!! OBVIOUSLY!! MWAHA!!"]
  }
}

def detect_intent(text):
    t = text.lower()
    patterns = [
        ('hunger',   r'\b(hungry|food|eat|pizza|burger|snack|lunch|dinner|breakfast|starving)\b'),
        ('tired',    r'\b(tired|sleep|sleepy|bed|rest|nap|exhausted|yawn)\b'),
        ('greeting', r'\b(hello|hi|hey|sup|howdy|yo)\b'),
        ('goodbye',  r'\b(bye|goodbye|later|see you|farewell|leaving)\b'),
        ('love',     r'\b(love|crush|adore|miss you|heart)\b'),
        ('hate',     r'\b(hate|despise|dislike|loathe)\b'),
        ('happy',    r'\b(happy|excited|great|amazing|joy|thrilled|yay)\b'),
        ('sad',      r'\b(sad|upset|cry|depressed|miserable|unhappy)\b'),
        ('angry',    r'\b(angry|mad|furious|rage|annoyed|frustrated)\b'),
        ('work',     r'\b(work|job|office|boss|meeting|deadline)\b'),
        ('money',    r'\b(money|pay|salary|broke|rich|cash|debt)\b'),
        ('school',   r'\b(school|study|homework|exam|test|teacher)\b'),
        ('request',  r'\b(help|assist|need you|can you|please|favor)\b'),
        ('apology',  r'\b(sorry|apologize|my bad|forgive|mistake)\b'),
        ('thanks',   r'\b(thanks|thank you|grateful|appreciate)\b'),
        ('bored',    r'\b(bored|boring|nothing to do|dull)\b'),
        ('success',  r'\b(win|won|victory|success|achieve)\b'),
        ('failure',  r'\b(fail|lost|lose|defeat|gave up)\b'),
        ('friend',   r'\b(friend|buddy|pal|bro|mate)\b'),
        ('plan',     r'\b(plan|idea|scheme|strategy)\b'),
        ('stop',     r'\b(stop|quit|enough|cease)\b'),
        ('fear',     r'\b(fear|scared|terrified|afraid)\b'),
        ('power',    r'\b(strong|powerful|unstoppable)\b'),
        ('weakness', r'\b(weak|pathetic|useless|worthless)\b'),
        ('betrayal', r'\b(betray|traitor|lied|cheat|deceive)\b'),
        ('laugh',    r'\b(laugh|funny|joke|lol|haha)\b'),
    ]
    for intent, pattern in patterns:
        if re.search(pattern, t):
            return intent
    if '?' in text:
        return 'question'
    return 'generic'

def villainify(text, mode):
    intent = detect_intent(text)
    pool = V.get(intent, {}).get(mode) or V['generic'][mode]
    return random.choice(pool), intent

# ── API ROUTES ─────────────────────────────────────────────────────────────────

@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    data = request.get_json()
    text = (data.get('text') or '').strip()
    mode = data.get('mode', '')
    if not text or mode not in ('menacing','dramatic','unhinged'):
        return jsonify({'error': 'text and valid mode required'}), 400

    output, intent = villainify(text, mode)

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO rewrites (input_text, output_text, mode, intent) VALUES (?,?,?,?)",
        (text, output, mode, intent)
    )
    rid = cur.lastrowid

    # update stats
    conn.execute(f"""
        UPDATE stats SET
            total_rewrites = total_rewrites + 1,
            {mode}_count   = {mode}_count + 1,
            villain_xp     = villain_xp + 10,
            last_used      = datetime('now','localtime')
        WHERE id = 1
    """)
    conn.commit()
    stats = dict(conn.execute("SELECT villain_xp FROM stats WHERE id=1").fetchone())
    conn.execute("UPDATE stats SET villain_rank=? WHERE id=1", (calc_rank(stats['villain_xp']),))
    conn.commit()
    row = conn.execute("SELECT villain_rank, villain_xp FROM stats WHERE id=1").fetchone()
    conn.close()

    return jsonify({
        'id': rid, 'output': output, 'intent': intent,
        'rank': row['villain_rank'], 'xp': row['villain_xp'],
        'xp_to_next': xp_to_next(row['villain_xp'])
    })

@app.route('/api/history')
def api_history():
    conn = get_db()
    rows = conn.execute("SELECT * FROM rewrites ORDER BY created_at DESC LIMIT 60").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/favourites')
def api_favourites():
    conn = get_db()
    rows = conn.execute("SELECT * FROM rewrites WHERE is_favourite=1 ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/favourite/<int:rid>', methods=['PATCH'])
def api_toggle_fav(rid):
    conn = get_db()
    conn.execute("UPDATE rewrites SET is_favourite = CASE WHEN is_favourite=1 THEN 0 ELSE 1 END WHERE id=?", (rid,))
    conn.commit()
    row = conn.execute("SELECT is_favourite FROM rewrites WHERE id=?", (rid,)).fetchone()
    conn.close()
    return jsonify({'is_favourite': row['is_favourite'] if row else 0})

@app.route('/api/rewrite/<int:rid>', methods=['DELETE'])
def api_delete(rid):
    conn = get_db()
    conn.execute("DELETE FROM rewrites WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/history', methods=['DELETE'])
def api_clear_history():
    conn = get_db()
    conn.execute("DELETE FROM rewrites WHERE is_favourite=0")
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    s = dict(conn.execute("SELECT * FROM stats WHERE id=1").fetchone())
    top_intents = [dict(r) for r in conn.execute(
        "SELECT intent, COUNT(*) as count FROM rewrites GROUP BY intent ORDER BY count DESC LIMIT 6"
    ).fetchall()]
    mode_breakdown = [dict(r) for r in conn.execute(
        "SELECT mode, COUNT(*) as count FROM rewrites GROUP BY mode"
    ).fetchall()]
    conn.close()
    s['top_intents'] = top_intents
    s['mode_breakdown'] = mode_breakdown
    s['xp_to_next'] = xp_to_next(s['villain_xp'])
    return jsonify(s)

@app.route('/api/random_villain_line')
def api_random():
    mode = request.args.get('mode', random.choice(['menacing','dramatic','unhinged']))
    intent = random.choice(list(V.keys()))
    pool = V[intent].get(mode, V['generic'][mode])
    return jsonify({'line': random.choice(pool), 'mode': mode, 'intent': intent})

# Serve frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    init_db()
    print("\n  ☠  VillanScript running → http://localhost:5000\n")
    app.run(debug=True, port=5000)
