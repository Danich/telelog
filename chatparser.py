import json
from collections import defaultdict
from typing import Dict, ItemsView, List

import matplotlib.pyplot as plt

from timecount import timecount


class ChatParser:
    def __init__(self, interpolation: int = 1, draw_only: List = (), graph_output: str = None):
        self._raw_data = None
        self._actions = set()
        self._messages_by_day = defaultdict(lambda: {'count': 0,
                                                     'by_author': defaultdict(int)})
        self._messages_by_user = defaultdict(int)
        self._ids_to_persons = {}
        self._pins_to_persons = defaultdict(int)
        self._images_to_persons = defaultdict(int)
        self._links_to_persons = defaultdict(int)
        self._stickers_to_persons = defaultdict(int)
        self._cancer_to_persons = {'voice_message': defaultdict(int),
                                   'video_message': defaultdict(int),
                                   'sticker': defaultdict(int),
                                   'animation': defaultdict(int)}
        self._counted_forwards = {'forwarders': defaultdict(int),
                                  'forwardees': defaultdict(int),
                                  'from_to': defaultdict(int)}
        self._counted_mentions = {'mentioners': defaultdict(int),
                                  'mentionees': defaultdict(int),
                                  'from_to': defaultdict(int)}

        self._interpolation = interpolation
        self._draw_only = draw_only
        self._draw_to = graph_output

    @timecount
    def load_data(self, path: str):
        with open(path, 'r') as f:
            self._raw_data = json.load(f)['messages']

    def count_messages(self):
        for item in self._raw_data:
            current_day = item['date'].split('T')[0]

            if 'action' in item:
                self._count_action(item)
                continue

            from_user = self._get_user_name_or_id(item)

            if 'forwarded_from' in item:
                self._count_forward(from_user, item)
                continue

            if 'photo' in item:
                self._count_photo(from_user)

            self._count_message_distribution(current_day, from_user)

            if type(item['text']) is list:
                self._count_links(from_user, item)

            if 'media_type' in item:
                self._count_cancer(from_user, item)

    def run(self):
        self.count_messages()
        self.print_stats()
        self.draw_graphs()

    def _count_cancer(self, from_user, item):
        if item['media_type'] not in self._cancer_to_persons:
            return
        self._cancer_to_persons[item['media_type']][from_user] += 1

    def _count_links(self, from_user, item):
        for i in item['text']:
            if type(i) is not dict:
                return
            if i['type'] == 'link':
                self._links_to_persons[from_user] += 1
                continue
            if i['type'] == 'mention':
                self._counted_mentions['mentionees'][i['text']] += 1
                self._counted_mentions['mentioners'][from_user] += 1
                self._counted_mentions['from_to'][f'{from_user} -> {i["text"]}'] += 1

    def _count_message_distribution(self, current_day, from_user):
        self._messages_by_day[current_day]['count'] += 1
        self._messages_by_day[current_day]['by_author'][from_user] += 1
        self._messages_by_user[from_user] += 1

    def _count_photo(self, from_user):
        self._images_to_persons[from_user] += 1

    def _count_forward(self, from_user, item):
        self._counted_forwards['forwarders'][from_user] += 1
        self._counted_forwards['forwardees'][item['forwarded_from']] += 1
        self._counted_forwards['from_to'][f'{from_user} -> {item["forwarded_from"]}'] += 1

    def _get_user_name_or_id(self, item):
        if item['from'] is None:
            from_user = item['from_id'] if item['from_id'] not in self._ids_to_persons else self._ids_to_persons[
                item['from_id']]
        else:
            from_user = item['from']
            self._ids_to_persons[item['from_id']] = from_user
        return from_user

    def _count_action(self, item):
        self._actions.add(item['action'])
        if item['action'] == 'pin_message':
            if item['actor'] is None:
                actor = item['actor_id'] \
                    if item['actor_id'] not in self._ids_to_persons \
                    else self._ids_to_persons[item['actor_id']]
            else:
                actor = item['actor']
            self._pins_to_persons[actor] += 1

    @timecount
    def print_stats(self):
        print('Самые пишущие: ')
        self._print_top(self._messages_by_user)
        print('=========')

        print('Форварды: ')
        print('  топ 10 форвардящих')
        self._print_top(self._counted_forwards['forwarders'])
        print('  топ 10 форвардуемых')
        self._print_top(self._counted_forwards['forwardees'])
        print('  больше всего любят форвардить')
        self._print_top(self._counted_forwards['from_to'])
        print('=========')

        print('Упоминания: ')
        print('  топ 10 упоминателей')
        self._print_top(self._counted_mentions['mentioners'])
        print('  топ 10 упоминаемых')
        self._print_top(self._counted_mentions['mentionees'])
        print('  больше всего любят звать')
        self._print_top(self._counted_mentions['from_to'])
        print('=========')

        print('Самые активные дни')
        count_by_days = {k: v['count'] for k, v in self._messages_by_day.items()}
        self._print_top(count_by_days)
        print('=========')

        print('Больше всех пинят:')
        self._print_top(self._pins_to_persons)
        print('=========')

        print('Больше всех картинок от:')
        self._print_top(self._images_to_persons)
        print('=========')

        print('Шлют ссылки:')
        self._print_top(self._links_to_persons)
        print('=========')

        print('Раковальня')
        print('  войсы')
        self._print_top(self._cancer_to_persons['voice_message'])
        print('  видео')
        self._print_top(self._cancer_to_persons['video_message'])
        print('  стикеры')
        self._print_top(self._cancer_to_persons['sticker'])
        print('  гифки')
        self._print_top(self._cancer_to_persons['animation'])
        print('=========')

    @timecount
    def print_service_info(self):
        print('Все действия: ')
        for i in self._actions:
            print(i, sep=',', end=' ')
        print('=========')
        print('Все пользователи: ')
        for user_id, names in self._ids_to_persons.items():
            print(f'{user_id}: {names}')

    @timecount
    def draw_graphs(self):
        only_users = self._filter_users(self._draw_only)
        iterate_range = only_users if len(only_users) > 0 else self._ids_to_persons.values()
        days_legend = dict()
        user_points = defaultdict(list)
        current_points = defaultdict(int)
        count = 0
        days_count = 0
        for day in self._messages_by_day.keys():
            for user in iterate_range:
                current_points[user] += self._messages_by_day[day]['by_author'][user]
            if count == self._interpolation:
                for user in iterate_range:
                    user_points[user].append(current_points[user] / self._interpolation)
                    current_points[user] = 0
                days_legend[days_count] = day
                count = 0
            else:
                count += 1
            days_count += 1
        plt.figure(figsize=(15, 9), dpi=300)
        for user in iterate_range:
            plt.plot(days_legend.keys(), user_points[user])
        ax = plt.gca()
        ax.tick_params(axis='x', labelrotation=90)
        plt.xticks(list(days_legend.keys()), list(days_legend.values()))

        plt.legend(iterate_range, loc=0, fancybox=True)
        if self._draw_to is None:
            plt.show()
        else:
            plt.savefig(self._draw_to)

    def _filter_users(self, users_list: List) -> List:
        if users_list is None: return []
        return [user for user in users_list if user in self._ids_to_persons.values()]

    def _print_top(self, input_dict: Dict):
        sorted_d = self._sort_dict_by_value(input_dict.items())
        self._print_top_dict(sorted_d)

    @staticmethod
    def _sort_dict_by_value(counted_tuple: ItemsView) -> Dict:
        return {k: v for k, v in sorted(counted_tuple, key=lambda item: item[1], reverse=True)}

    @staticmethod
    def _print_top_dict(input_dict: Dict, counter_max: int = 10):
        counter = 1
        for day, count in input_dict.items():
            print(f'{counter}: {day} - {count}')
            counter += 1
            if counter > counter_max:
                break
