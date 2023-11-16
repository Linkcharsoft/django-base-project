import pandas as pd

import time

from io import StringIO

import requests

from django.core.management.base import BaseCommand
from django.conf import settings

from platform_configurations import models 
from django_base.base_utils.utils import (
    get_abstract_country_model,
)

class Command(BaseCommand):
    """Django command to populate location models."""

    base_data_url = 'https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/'

    data_uls = {
        'country':f'{base_data_url}/countries.json',
        'state':f'{base_data_url}/countries+states.json',
        'city':f'{base_data_url}/countries+states+cities.json'
    }

    model_creator = {
        'country': '_create_country_object',    
        'state': '_create_state_object',
        'city': '_create_city_object'
    }

    related = {
        'country': [],
        'state': ['states'],
        'city': ['states', 'states__cities']
    }

    base_country_fields = [
        'name',
        'iso3',
        'latitude',
        'longitude',
    ]

    extended_country_fields = base_country_fields + [
        'iso2',
        'numeric_code',
        'phone_code',
        'currency',
        'currency_name',
        'currency_symbol'
    ]

    def _get_data_url(self):
        if not settings.INCLUDE_LOCATION:
            raise Exception('Location is not included in settings')
        return self.data_uls[settings.LOCATION_SCOPE]

    def _get_data(self):
        response = requests.get(self._get_data_url())
        if response.status_code != 200:
            raise Exception('Error getting data from url')
        data = pd.read_json(StringIO(response.text))
        return data

    def _get_all_countries(self):
        return models.Country.objects.prefetch_related(
                *self.related['country']
            ).all()

    def _update_country(self, item, all_countries, counties_to_update):
        country = all_countries.get(name=item[0])
        country.name = item[0]
        country.iso3=item[1]
        country.latitude=item[18]
        country.longitude=item[19]
        country.iso2 = item[2]
        country.numeric_code = item[3]
        country.phone_code = item[4]
        country.currency = item[7]
        country.currency_name = item[8]
        country.currency_symbol = item[9]
        counties_to_update.append(country)

    def _update_state(self, item, all_states, states_to_update):
        state = all_states.get(json_id=item['id'])
        state.name = item['name']
        state.state_code = item['state_code']
        state.latitude = item['latitude']
        state.longitude = item['longitude']
        states_to_update.append(state)

    def _create_country_object(self, item, *args):
        base_model_fields = {
            'name': item[0],
            'iso3': item[1],
            'latitude': item[18],
            'longitude': item[19],
        }
        if 'AbstactExpandedCountry' in models.Country.__bases__:
            base_model_fields.update({
                'iso2': item[2],
                'numeric_code': item[3],
                'phone_code': item[4],
                'currency': item[7],
                'currency_name': item[8],
                'currency_symbol': item[9]
            })

        return models.Country(**base_model_fields)

    def _create_state_object(self, item, country):
        return models.State(
            json_id=item['id'],
            name=item['name'],
            state_code=item['state_code'],
            latitude=item['latitude'],
            longitude=item['longitude'],
            country=country
        )

    def _create_city_object(self, item):
        pass

    def _add_to_create_list(self, model, item, items_to_create, country=None):
        item_creator = getattr(self, self.model_creator[model])
        items_to_create.append(item_creator(item, country))

    def handle(self, *args, **options):
        st = time.time()
        """Handle the command."""
        data = self._get_data()

        all_countries = self._get_all_countries()
        all_countries_names = all_countries.values_list('name', flat=True)
        counties_to_create = []
        counties_to_update = []
        for item in data.values:
            if item[0] not in all_countries_names:
                self._add_to_create_list('country', item, counties_to_create)
            else:
                self._update_country(item, all_countries, counties_to_update)

        if counties_to_create:
            print(f'Creating countries {len(counties_to_create)}')
            models.Country.objects.bulk_create(counties_to_create)
        if counties_to_update:
            fields = self.extended_country_fields if \
                    'AbstactExpandedCountry' in models.Country.__bases__ \
                    else self.base_country_fields
            print(f'Updating countries {len(counties_to_update)}')
            models.Country.objects.bulk_update(counties_to_update, fields)

        if settings.LOCATION_SCOPE != 'country':
            states_to_create = []
            states_to_update = []
            for item in data.values:
                country = all_countries.get(name=item[0])
                all_country_states = country.states.all()
                all_country_states_names = all_country_states.values_list('name', flat=True)
                for state in item[22]:
                    if state['name'] not in all_country_states_names:
                        self._add_to_create_list('state', state, states_to_create, country)
                    else:
                        self._update_state(state, all_country_states, states_to_update)

            if states_to_create:
                print(f'Creating states {len(states_to_create)}')
                try:
                    models.State.objects.bulk_create(states_to_create)
                except Exception as e:
                    print(e)
                    raise e
            if states_to_update:
                print(f'Updating states {len(states_to_update)}')
                models.State.objects.bulk_update(states_to_update, ['name', 'state_code', 'latitude', 'longitude'])

        # get the end time
        et = time.time()

        # get the execution time
        elapsed_time = et - st
        print('Execution time:', elapsed_time, 'seconds')