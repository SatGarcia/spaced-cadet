import requests, sys, json, click, csv
import urllib.parse as up

USER_EMAIL = 'teacher@email.com'
USER_PASSWORD = 'password123!'

def get_logged_in_session(base_url):
    s = requests.Session()

    # log in to get cookies
    r = s.post(f'{base_url}/api/login',
               json={'email': USER_EMAIL, 'password': USER_PASSWORD})

    if r.status_code != 200:
        print("ERROR: Could not log in!")
        print(json.dumps(r.json(), indent=4))
        sys.exit()

    # setup header for double submit token
    s.headers["X-CSRF-TOKEN"] = s.cookies.get('csrf_access_token')

    return s


@click.group()
def api():
    pass


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
@click.option('--public', is_flag=True)
@click.argument('filename')
def add_objectives(base_url, public, filename):
    """ Program that uploads learning objectives from a given file. """

    s = get_logged_in_session(base_url)

    with open(filename, 'r') as objectives_file:
        for line in objectives_file:
            o = {
                'description': line.strip(),
                'public': True,
            }

            r = s.post(f"{base_url}/api/objectives",
                              json=o)

            print("Status Code:", r.status_code)
            print(r.json())

    r = s.get(f"{base_url}/api/objectives")
    print("Status Code:", r.status_code)
    print(r.json())


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
@click.argument('filename')
@click.argument('textbook_id', type=int)
def add_textbook_sections(base_url, filename, textbook_id):
    """ Program that uploads textbook sections (with topics) from a given file. """

    s = get_logged_in_session(base_url)

    r = s.get(f"{base_url}/api/topics")
    if r.status_code != 200:
        print("Failed to fetch topics. Exiting.")
        return

    topics = r.json()['topics']
    topic_mapping = { t['text']: t['id'] for t in topics }

    failed_new = {}
    failed_add_topics = {}
    failed_topics = {}

    with open(filename, newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        header = next(csv_reader)
        for row in csv_reader:
            #print([c for c in row if len(c.strip()) != 0])
            tb_section = {
                'number': row[0].strip(),
                'title': row[1].strip(),
            }

            r = s.post(f"{base_url}/api/textbook/{textbook_id}/sections",
                              json=tb_section)

            if r.status_code != 200:
                failed_new[tb_section['number']] = r.json()
                continue

            textbook_section = r.json()['textbooksection']

            section_topics = [col for col in row[2:] if len(col.strip()) != 0]
            section_topic_ids = []
            non_existent_topics = []

            for t in section_topics:
                if t in topic_mapping:
                    section_topic_ids.append(topic_mapping[t])
                else:
                    non_existent_topics.append(t)

            if len(section_topic_ids) > 0:
                r = s.post(f"{base_url}/api/textbook/{textbook_id}/section/{textbook_section['id']}/topics",
                           json={'ids': section_topic_ids})

                if r.status_code != 200:
                    failed_add_topics[tb_section['number']] = r.json()
                    continue

            if len(non_existent_topics) > 0:
                    failed_topics[tb_section['number']] = non_existent_topics

    """
    with open(filename, 'r') as textbook_file:
        for line in textbook_file:
            t = {
                'text': line.strip(),
            }

            r = s.post(f"{base_url}/api/topics",
                              json=t)

            if r.status_code != 200:
                failed[line] = r.json()
    """

    if len(failed_new) > 0:
        print("Failed To Create Sections:", ", ".join(failed_new.keys()))
    if len(failed_add_topics) > 0:
        print("Failed To Add Topics:", ", ".join(failed_add_topics.keys()))
    if len(failed_topics) > 0:
        baddies = [f"{num}: {topics}" for num, topics in failed_topics.items()]
        print("Non-existent Topics:\n\t", "\n\t".join(baddies))


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
@click.argument('filename')
def add_topics(base_url, filename):
    """ Program that uploads topics from a given file. """

    s = get_logged_in_session(base_url)

    failed = {}

    with open(filename, 'r') as topics_file:
        for line in topics_file:
            t = {
                'text': line.strip(),
            }

            r = s.post(f"{base_url}/api/topics",
                              json=t)

            if r.status_code != 200:
                failed[line] = r.json()

    if len(failed) > 0:
        print("Failed:", ", ".join(failed.keys()))


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
def get_topics(base_url):
    """ Program that uploads topics from a given file. """

    s = get_logged_in_session(base_url)
    r = s.get(f"{base_url}/api/topics")

    print("Status Code:", r.status_code)
    print(json.dumps(r.json(), indent=4))


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
@click.argument("query")
def search_topics(base_url, query):
    """ Program that uploads topics from a given file. """

    s = get_logged_in_session(base_url)
    r = s.get(f"{base_url}/api/topics?q={up.quote(query)}")

    print("Status Code:", r.status_code)
    print(json.dumps(r.json(), indent=4))


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
@click.argument('course_id')
@click.argument('assessment_id')
def get_course_assessment_questions(base_url, course_id, assessment_id):
    """ Program that gets the questions assigned to a specific course. """

    s = get_logged_in_session(base_url)
    r = s.get(f"{base_url}/api/course/{course_id}/assessment/{assessment_id}/questions")

    print("Status Code:", r.status_code)
    print(json.dumps(r.json(), indent=4))


@api.command()
@click.option('--base_url', default='http://localhost:5000',
              help='URL for the server')
@click.option('--topics_query',
              help='Query string for topics to limit returned objectives')
@click.option('--query',
              help='Query string to search with')
def get_objectives(base_url, topics_query, query):
    """ Program that uploads topics from a given file. """

    s = get_logged_in_session(base_url)

    request_params = ''
    if query:
        request_params += f'?q={up.quote(query)}'
    if topics_query:
        if len(request_params) == 0:
            request_params += '?'
        else:
            request_params += '&'

        request_params += f'topics_q={up.quote(topics_query)}'

    r = s.get(f"{base_url}/api/objectives/search{request_params}")

    print("Status Code:", r.status_code)
    print(json.dumps(r.json(), indent=4))


if __name__ == "__main__":
    api()
