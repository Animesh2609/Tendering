"""Experimental choices: shared implementations, intentionally different studies."""

SEED = 42
VECTORIZER_SETTINGS = dict(lowercase=False, tokenizer=str.split, token_pattern=None,
                           max_features=3000, min_df=3, max_df=0.90)

SIX_CATEGORIES = ['comp.graphics',
 'misc.forsale',
 'rec.sport.baseball',
 'sci.med',
 'sci.space',
 'talk.politics.guns']

SUPERGROUPS = {'Computing': ['comp.graphics',
               'comp.os.ms-windows.misc',
               'comp.sys.ibm.pc.hardware',
               'comp.sys.mac.hardware',
               'comp.windows.x'],
 'Digital technology and engineering': ['sci.crypt', 'sci.electronics'],
 'Health and space science': ['sci.med', 'sci.space'],
 'Recreation and consumer exchange': ['misc.forsale',
                                      'rec.autos',
                                      'rec.motorcycles',
                                      'rec.sport.baseball',
                                      'rec.sport.hockey'],
 'Religion and worldview': ['alt.atheism', 'soc.religion.christian', 'talk.religion.misc'],
 'Politics and international affairs': ['talk.politics.guns',
                                        'talk.politics.mideast',
                                        'talk.politics.misc']}

CATEGORY_QUERIES = {'alt.atheism': 'atheism atheist religion belief',
 'comp.graphics': 'computer graphics rendering image pixels',
 'comp.os.ms-windows.misc': 'windows operating system microsoft files',
 'comp.sys.ibm.pc.hardware': 'IBM PC hardware disk memory computer',
 'comp.sys.mac.hardware': 'Apple Macintosh Mac hardware computer',
 'comp.windows.x': 'X Window System display server windows',
 'misc.forsale': 'for sale price shipping offer',
 'rec.autos': 'car automobile engine dealer',
 'rec.motorcycles': 'motorcycle bike riding helmet',
 'rec.sport.baseball': 'baseball players team season game',
 'rec.sport.hockey': 'hockey team NHL puck season',
 'sci.crypt': 'cryptography encryption key security',
 'sci.electronics': 'electronics circuit voltage resistor',
 'sci.med': 'medical doctor disease treatment health',
 'sci.space': 'space NASA spacecraft orbit planet',
 'soc.religion.christian': 'Christian church Bible Jesus faith',
 'talk.politics.guns': 'gun control firearms second amendment',
 'talk.politics.mideast': 'Middle East Israel Arab Palestinian',
 'talk.politics.misc': 'government election political policy',
 'talk.religion.misc': 'religion religious belief faith'}

SUPERGROUP_QUERIES = {'Computing': 'computer graphics software hardware operating systems windows',
 'Digital technology and engineering': 'electronics circuits encryption cryptography hardware',
 'Health and space science': 'medicine health disease doctor space NASA planet',
 'Recreation and consumer exchange': 'cars motorcycles baseball hockey sports sale price',
 'Religion and worldview': 'religion atheist christian belief faith god',
 'Politics and international affairs': 'politics government guns international middle east '
                                       'policy'}

QUERY_BANK = {'comp.graphics': [('direct', 'computer graphics rendering image pixels'),
                   ('paraphrase', 'raster visualization color drawing display'),
                   ('related_terms', 'jpeg gif image resolution file format')],
 'misc.forsale': [('direct', 'for sale price shipping offer'),
                  ('paraphrase', 'selling item cost postage interested'),
                  ('related_terms', 'available purchase asking price contact')],
 'rec.sport.baseball': [('direct', 'baseball players team season game'),
                        ('paraphrase', 'pitcher batter inning home run'),
                        ('related_terms', 'major league baseball statistics runs')],
 'sci.med': [('direct', 'medical doctor disease treatment health'),
             ('paraphrase', 'patient symptom diagnosis medication clinical'),
             ('related_terms', 'hospital therapy drug research study')],
 'sci.space': [('direct', 'space NASA spacecraft orbit planet'),
               ('paraphrase', 'shuttle mission satellite launch moon'),
               ('related_terms', 'astronomy universe planetary exploration')],
 'talk.politics.guns': [('direct', 'gun control firearms second amendment'),
                        ('paraphrase', 'weapon legislation rights handgun rifle'),
                        ('related_terms', 'firearm policy congress law')]}

EXPERIMENTS = {'PLSA_Baseline': {'corpus': 'all20', 'test_size': 0.25, 'validation': False},
 'PLSA_Retrieval_Scoring_Investigation': {'corpus': 'six_categories',
                                          'test_size': 0.25,
                                          'validation': False},
 'Six_Category_Experiment': {'corpus': 'supergroups', 'test_size': 0.2, 'validation': False},
 'Bagging_Experiment': {'corpus': 'supergroups', 'test_size': 0.2, 'validation': False},
 'Retrieval_Validation_Query_Study': {'corpus': 'six_categories',
                                      'test_size': 0.2,
                                      'validation': True},
 'All20_K_Study': {'corpus': 'all20', 'test_size': 0.2, 'validation': True}}
