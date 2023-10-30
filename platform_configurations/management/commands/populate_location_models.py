import pandas as pd

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

    def _update_country(self, item, all_countries):
        print(item)
        country = all_countries.get(name=item[1])
        country.name = item[1]
        country.iso_3=item[2]
        country.latitude=item[19]
        country.longitude=item[20]
        country.iso_2 = item[3]
        country.numeric_code = item[4]
        country.phone_code = item[5]
        country.currency = item[7]
        country.currency_name = item[8]
        country.currency_symbol = item[9]
        country.save()

    def _create_country_object(self, item):
        if 'AbstactExpandedCountry' in models.Country.__bases__:
            return models.Country(
                    # Base Fields
                    name=item[1],
                    iso_3=item[2],
                    latitude=item[19],
                    longitude=item[20],

                    # Extended fields
                    iso_2=item[3],
                    numeric_code=item[4],
                    phone_code=item[5],
                    currency=item[7],
                    currency_name=item[8],
                    currency_symbol=item[9]
                )
        else:
            return models.Country(
                    # Base Fields
                    name=item[1],
                    iso3=item[2],
                    latitude=item[19],
                    longitude=item[20],
                )

    def _create_state_object(self, item):
        pass

    def _create_city_object(self, item):
        pass

    def _add_to_create_list(self, model, item, items_to_create):

        item_creator = getattr(self, self.model_creator[model])
        items_to_create.append(item_creator(item))

    def handle(self, *args, **options):
        """Handle the command."""
        data = self._get_data()

        all_countries = self._get_all_countries()
        all_countries_names = all_countries.values_list('name', flat=True)
        counties_to_create = []
        for item in data.values:
            if item[1] not in all_countries_names:
                self._add_to_create_list('country', item, counties_to_create)
            else:
                print(f'Updating {item[1]}')
                self._update_country(item, all_countries)

        models.Country.objects.bulk_create(counties_to_create)

