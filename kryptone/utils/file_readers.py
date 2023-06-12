import json, csv


def read_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = f.read()
    return data


def read_json_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = json.load(f)
        return data


def write_json_document(filename, data):
    """Writes data to a JSON file"""
    with open(filename, mode='w+', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def write_csv_document(filename, data):
    """Writes data to a CSV file"""
    with open(filename, mode='w', newline='\n', encoding='utf-8') as f:
        writer = csv.writer(f)

        if isinstance(data, set):
            data = list(data)

        if not isinstance(data, list):
            data = [data]
            
        writer.writerows(data)
