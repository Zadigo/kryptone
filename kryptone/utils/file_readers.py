import json, csv


def read_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = f.read()
    return data


def write_json_document(filename, data):
    with open(filename, mode='w+', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def read_json_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = json.load(f)
        return data


def write_csv_document(filename, data):
    with open(filename, mode='w', newline='\n', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not isinstance(data, list):
            data = [data]
        writer.writerow(data)