from dataclasses import dataclass
import json
import os
import time
from typing import Dict, List

import requests


@dataclass
class Phrase:
    intent: str
    is_bot: bool
    phrases: List[str]
    replies: List['Phrase']

    def json(self, intents):
        result = self.__dict__
        if result['is_bot']:
            del result['intent']
        replies = []
        if result['replies']:
            for reply_phrase in result['replies']:
                if isinstance(reply_phrase, Phrase):
                    if reply_phrase.intent not in intents:
                        intents.add(reply_phrase.intent)
                        replies.append(reply_phrase.json(intents))
        result['replies'] = replies

        return result


def processing_phrases(phrases: Dict[str, 'Phrase']) -> list:
    intents_set = set()
    intents_set.add('start')
    result = [phrases['start'].json(intents_set)]
    diff = set(phrases.keys()).difference(intents_set)
    if diff:
        for intent in diff:
            result.append(phrases[intent].json(intents_set))

    return result


def get_intent(text: str) -> str:
    count_of_tries = 0
    url = f'https://sandbox.twin24.ai/parse?q={text}'
    while True:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != requests.codes.ok:
                count_of_tries += 1
                time.sleep(1)
                if count_of_tries >= 10:
                    r.raise_for_status()
            json_r = r.json()
            return json_r['intent']['name']

        except Exception as e:
            print(e)


def analyze_calls(calls: dict) -> Dict[str, 'Phrase']:
    phrases = {}
    for call in calls.values():
        intent = 'start'
        previous_intent = None
        for sentence in call:
            # получаем intent
            if not sentence['is_bot']:
                intent = get_intent(sentence['text'])
            elif intent != 'start':
                intent += '_reply'

            # получаем фразу по intent и обновляем ее или создаем новую
            phrase = phrases.get(intent)
            if not phrase:
                phrase = Phrase(
                    intent=intent,
                    is_bot=sentence['is_bot'],
                    phrases=[sentence['text']],
                    replies=[],
                )
                phrases[intent] = phrase
            elif sentence['text'] not in phrase.phrases:
                phrase.phrases.append(sentence['text'])

            if previous_intent:
                previous_phrase = phrases.get(previous_intent)
                if previous_phrase and not phrase in previous_phrase.replies:
                    previous_phrase.replies.append(phrase)

            previous_intent = intent

    return phrases


def prepare_data() -> dict:
    all_calls: dict = {}
    for file_name in range(1, 6):
        all_calls[file_name] = []
        with open(f'{os.getcwd()}/dialogs/{file_name}.json', 'r') as json_file:
            data = json.load(json_file)
            for row in data:
                all_calls[file_name].append(row)

    return all_calls


def main():
    calls = prepare_data()
    phrases = analyze_calls(calls)
    result = processing_phrases(phrases)

    print(result)
    with open('result.json', 'w+') as f:
        json.dump([result], f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
