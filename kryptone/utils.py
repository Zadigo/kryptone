import json


def write_json_document(filename, data):
    with open(filename, mode='w+', encoding='utf-8') as f:
        # data = {'urls_to_visit': [], 'visited_urls': ['http://example.com']}
        json.dump(data, f, indent=4)


def read_json_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = json.load(f)
        return data
