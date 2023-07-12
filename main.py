import argparse
import requests
import csv


DEFAULT_ENDPOINT_URL = "https://api.newrelic.com/graphql"
DEFAULT_DASHBOARD_OUTPUT_FILENAME = "dashboards.csv"
DEFAULT_NRUSAGE_DASHBOARDS_OUTPUT_FILENAME = "nrusage-dashboards.csv"

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('api_key', help='API key for GraphQL endpoint')
parser.add_argument('--endpoint-url', help=f'URL for GraphQL endpoint (default: {DEFAULT_ENDPOINT_URL})', default=DEFAULT_ENDPOINT_URL)
# parser.add_argument('--query', help='GraphQL query')
parser.add_argument('--output-filename', help=f'Output CSV file name (default: {DEFAULT_DASHBOARD_OUTPUT_FILENAME})', default=DEFAULT_DASHBOARD_OUTPUT_FILENAME)
args = parser.parse_args()

db_query = """{
  actor {
    entitySearch(queryBuilder: {type: DASHBOARD}) {
      count
      results {
        nextCursor
        entities {
          ... on DashboardEntityOutline {
            guid
            name
            accountId
          }
        }
      }
    }
  }
}"""

db_query_nextCursor = """{
  actor {
    entitySearch(queryBuilder: {type: DASHBOARD}) {
      results(cursor: "") {
        nextCursor
        entities {
          ... on DashboardEntityOutline {
            guid
            name
            accountId
          }
        }
      }
    }
  }
}"""


def handle_request(api_key, endpoint_url, query):
    # Set the request headers
    headers = {
        'Content-Type': 'application/json',
        'API-Key': f'{api_key}',
    }

    # Define the request payload
    payload = {
        'query': query,
    }

    # Send the request to the endpoint
    response = requests.post(endpoint_url, headers=headers, json=payload)

    # Check if the response is not 200 OK
    if response.status_code != 200:
        raise Exception(f'Request failed with status code {response.status_code}')

    # Get the response data in JSON format
    data = response.json()

    return data


def get_dashboard_entities(data, output_filename):
    # Search for entity data to process
    entity_data = None
    for key, value in data.items():
        if key == 'actor':
            entity_data = value
            break

    # If "actor" key not found, raise an exception
    if not entity_data:
        raise Exception('Could not find "entitySearch" key in response data')

    # Parse the response data to get the field names
    field_names = []
    for row in entity_data['entitySearch']['results']['entities']:
        field_names += list(row.keys())
    field_names = list(set(field_names))

    next_cursor = entity_data['entitySearch']['results']['nextCursor']

    # Open a CSV file in write mode
    with open(output_filename, mode='w', newline='') as file:

        # Create a CSV writer object
        writer = csv.writer(file)

        # Write the header row
        writer.writerow(field_names)

        # Write the data rows
        while True:
            for row in entity_data['entitySearch']['results']['entities']:
                writer.writerow([row.get(field, "") for field in field_names])
            if next_cursor:
                next_data = handle_request(args.api_key, args.endpoint_url, db_query_nextCursor)
                entity_data = next_data['actor']['entitySearch']['results']['entities']
                next_cursor = next_data['actor']['entitySearch']['results']['nextCursor']
            else:
                break


def get_dashboard_definition(guid):
    # build your query
    widget_query = """
    {
      actor {
        entity(guid: "REPLACE_WITH_ENTITY_GUID") {
          ... on DashboardEntity {
            guid
            name
            accountId
            pages {
              widgets {
                rawConfiguration
              }
            }
          }
        }
      }
    }
    """
    widget_query = widget_query.replace('REPLACE_WITH_ENTITY_GUID', guid)
    # call handle_request
    res = handle_request(args.api_key, args.endpoint_url, widget_query)
    # return
    return res


try:
    data = handle_request(args.api_key, args.endpoint_url, db_query)
    get_dashboard_entities(data['data'], args.output_filename)
    with open(args.output_filename, mode='r', newline='') as file:
        reader = csv.DictReader(file)

        with open(DEFAULT_NRUSAGE_DASHBOARDS_OUTPUT_FILENAME, mode='w', newline='') as db_file:
            writer = csv.writer(db_file)
            writer.writerow(['accountId', 'name', 'guid', 'nrql'])
            for line in reader:
                guid = line['guid']
                db = get_dashboard_definition(guid)
                pages = db['data']['actor']['entity']['pages']
                if pages:
                    for page in pages:
                        for widget in page['widgets']:
                            if widget['rawConfiguration'] != {} and 'nrqlQueries' in widget['rawConfiguration']:
                                for nrql in widget['rawConfiguration']['nrqlQueries']:
                                    # search the query for NrUsage and NrDailyUsage
                                    if 'NrUsage' in nrql['query'] or 'NrDailyUsage' in nrql['query']:
                                        writer.writerow([line['accountId'], line['name'], line['guid'], nrql['query']])
                else:
                    pass
except Exception as e:
    print(f'Error: {e}')

