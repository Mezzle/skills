DOCUMENTS = {
    'alice-note': {'tenant': 'alice', 'text': 'Alice private note'},
    'bob-note': {'tenant': 'bob', 'text': 'Bob private note'},
}


def read_document(tenant, document_id):
    document = DOCUMENTS[document_id]
    if document['tenant'] != tenant:
        raise PermissionError('Wrong tenant')
    return document['text']
