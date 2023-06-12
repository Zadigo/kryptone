import redis


class RedisConnection:
    def __init__(self):
        self.host = None
        self.port = None
        self.password = None
        self.connection = redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password
        )


# def clean_information_list(items):
#     exclude = ['lundi', 'mardi', 'mercredi', 'jeudi',
#                 'vendredi', 'samedi', 'dimanche']
#     a = []
#     for text in items:
#         if text in exclude:
#             continue
#         a.append(text)

#     c = []
#     for text in a:
#         logic = [
#             text.startswith('lundi'),
#             text.startswith('Ouvert'),
#             text.startswith('Envoyer vers'),
#             text.startswith('Suggérer')
#         ]
#         if any(logic):
#             continue
#         c.append(text)
#     return c

# a = [
#     "jeudi",
#     "mercredi",
#     "Ouvert ⋅ Ferme à 19:30",
#     "QJPP+X9 Cany-Barville",
#     "Envoyer vers votre téléphone",
#     "lundi",
#     "vendredi",
#     "Suggérer de nouveaux horaires",
#     "lundi06:00–19:30mardiFermémercredi06:00–19:30jeudi06:00–19:30vendredi06:00–19:30samedi06:00–19:30dimanche07:00–19:30Suggérer de nouveaux horaires",
#     "51 Rue du Général de Gaulle, 76450 Cany-Barville",
#     "samedi",
#     "02 35 57 01 62",
#     "dimanche",
#     "mardi"
# ]
# print(list(clean_information_list(a)))
