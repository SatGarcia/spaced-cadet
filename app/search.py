import click

from flask import current_app
from flask.cli import AppGroup, with_appcontext


search_cli = AppGroup('search')

@search_cli.command('reindex')
@with_appcontext
def reindex_all():
    from app.db_models import SearchableMixin
    if not current_app.elasticsearch:
        click.echo("Elasticsearch is not configured and/or running.")
        return

    for cls in SearchableMixin.__subclasses__():
        index_name = cls.__tablename__
        click.echo(f"Reindexing {index_name}")
        cls.reindex()

@search_cli.command('moo')
@with_appcontext
def moo():
    from app.db_models import SearchableMixin
    if not current_app.elasticsearch:
        click.echo("Elasticsearch is not configured and/or running.")
        return

    foo = current_app.elasticsearch.indices.get_settings('topic')
    #click.echo(foo)

    bar = {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "english"
                    }
                }
            }

    baz = {
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "english"
                        }
                    }
                }
            }

    #current_app.elasticsearch.indices.put_mapping(bar, index='topic')
    current_app.elasticsearch.indices.close('topic')
    current_app.elasticsearch.indices.put_settings(baz, index='topic')
    current_app.elasticsearch.indices.open('topic')

    foo = current_app.elasticsearch.indices.get_settings('topic')
    #click.echo(foo)

    foo = current_app.elasticsearch.indices.analyze(body={'text': 'The quick brown fox jumped over the lazy brown dog'}, index='objective')
    click.echo(foo)

def add_to_index(index, model):
    if not current_app.elasticsearch:
        return

    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, id=model.id, body=payload)


def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def clear_index(index):
    """ Clears the contents of the given index. """
    if not current_app.elasticsearch:
        return

    # If the index exists, delete it. Otherwise, just create the empty index.
    if current_app.elasticsearch.indices.exists(index):
        current_app.elasticsearch.indices.delete(index)

    current_app.elasticsearch.indices.create(index)


def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0

    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'multi_match': {'query': query, 'analyzer': 'english', 'fields': ['*']}},
              'from': page * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']


def init_app(app):
    """ Initializes the app by making sure all indicies are created. """
    from app.db_models import SearchableMixin
    for cls in SearchableMixin.__subclasses__():
        index_name = cls.__tablename__
        if not app.elasticsearch.indices.exists(index_name):
            app.logger.info(f"Creating index {index_name}")
            app.elasticsearch.indices.create(index_name)

