import os

from flask import Flask, request, jsonify
import logging
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

characters = {
    'Супер-кот': ['997614/d042f08fa611328e5e58',
                  'Загаданный персонаж спасает Париж',
                  'Загаданный персонаж имеет суперспособности'],
    'Вольт': ['1521359/7b7298f35df9f078ffc0',
              'Загаданный персонаж - собака-актёр',
              'Загаданный персонаж имеет чёрный рисунок в виде молнии на боку'],
    'Джуди': ['1533899/174ed6141583784daa04',
              'Загаданный персонаж - первый кролик в полиции',
              'Загаданный персонаж расследует дело в команде с лисом'],
    'Рэми': ['1656841/71bca346122679689d8b',
             'Загаданный персонаж обладает исключительным чувством вкуса',
             'Загаданный персонаж понимает человеческую речь'],
    'Флин': ['1533899/fe43dbdcb29f9ab146a2',
             'Загаданный персонаж при первом появлении представляется именем из любимой книги',
             'Загаданный персонаж является разбойником']
}

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    character_id = req['session']['character_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Меня зовут Алиса, а как зовут тебя?'
        sessionStorage[character_id] = {
            'first_name': None,  # здесь будет храниться имя
            'game_started': False  # здесь информация о том, что пользователь начал игру. По умолчанию False
        }
        return

    if sessionStorage[character_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[character_id]['first_name'] = first_name
            # создаём пустой массив, в который будем записывать персонажей, которых пользователь уже отгадал
            sessionStorage[character_id]['guessed_characters'] = []
            # Предлагаем пользователю сыграть и два варианта ответа "Да" и "Нет".
            res['response']['text'] = (f'Приятно познакомиться, {first_name.title()}.'
                                       f'Давай сыграем в "Угадай персонажа мультфильма по силуэту"?')
            res['response']['buttons'] = [
                {
                    'title': 'Давай!',
                    'hide': True
                },
                {
                    'title': 'Нет.',
                    'hide': True
                }
            ]
    else:
        # У нас уже есть имя, и теперь мы ожидаем ответ на предложение сыграть.
        # В sessionStorage[character_id]['game_started'] хранится True или False в зависимости от того,
        # начал пользователь игру или нет.
        if not sessionStorage[character_id]['game_started']:
            # игра не начата, значит мы ожидаем ответ на предложение сыграть.
            if ("Давай!") in req['request']['nlu']['tokens']:
                # если пользователь согласен, то проверяем не отгадал ли он уже всех персонажей.
                # По схеме можно увидеть, что здесь окажутся и пользователи, которые уже отгадывали персонажей
                if len(sessionStorage[character_id]['guessed_characters']) == 5:
                    # если все пять персонажей уже отгаданы, то заканчиваем игру
                    res['response']['text'] = 'Ты отгадал всех персонажей!'
                    res['end_session'] = True
                else:
                    # если есть неотгаданные персонажи, то продолжаем игру
                    sessionStorage[character_id]['game_started'] = True
                    # номер попытки, чтобы показывать фото по порядку
                    sessionStorage[character_id]['attempt'] = 1
                    # функция, которая выбирает город для игры и показывает фото
                    play_game(res, req)
            elif 'Нет.' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно, как-нибудь в другой раз!'
                res['end_session'] = True
            else:
                res['response']['text'] = 'Не поняла ответа! Так будем играть или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Будем!',
                        'hide': True
                    },
                    {
                        'title': 'Нет.',
                        'hide': True
                    }
                ]
        else:
            play_game(res, req)


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1:
        # если попытка первая, то случайным образом выбираем персонажа для гадания
        character = random.choice(list(characters))
        # выбираем его до тех пор пока не выберем персонажа, которого нет в sessionStorage[user_id]['guessed_characters']
        while character in sessionStorage[user_id]['guessed_characters']:
            character = random.choice(list(characters))
        # записываем город в информацию о пользователе
        sessionStorage[user_id]['character'] = character
        # добавляем в ответ картинку
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за персонаж?'
        res['response']['card']['image_id'] = characters[character][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
    else:
        # сюда попадаем, если попытка отгадать не первая
        character = sessionStorage[user_id]['character']
        # проверяем есть ли правильный ответ в сообщение
        if get_character(req) == character:
            # если да, то добавляем персонажа к sessionStorage[user_id]['guessed_characters'] и
            # отправляем пользователя на второй круг. Обратите внимание на этот шаг на схеме.
            res['response']['text'] = 'Правильно! Сыграем ещё?'
            sessionStorage[user_id]['guessed_characters'].append(character)
            sessionStorage[user_id]['game_started'] = False
            return
        else:
            # если нет
            if attempt == 4:
                # если попытка четвёртая, то значит, что подсказок больше нет.
                # В этом случае говорим ответ пользователю,
                # добавляем персонажа к sessionStorage[user_id]['guessed_characters'] и отправляем его на второй круг.
                # Обратите внимание на этот шаг на схеме.
                res['response']['text'] = f'Вы пытались. Это {character.title()}. Сыграем ещё?'
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_characters'].append(character)
                return
            elif attempt == 3:
                # иначе показываем следующую картинку
                res['response']['card'] = {}
                res['response']['card']['title'] = 'Неверно. У тебя осталась одна попытка. Хочешь получить подсказку?'
                res['response']['buttons'] = [
                    {
                        'title': 'Хочу!',
                        'hide': True
                    },
                    {
                        'title': 'Не-а.',
                        'hide': True
                    }
                ]
                if "Хочу!" in res['request']['nlu']['tokens']:
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['text'] = 'Держи:'
                    res['response']['card']['text'] = characters[character][attempt - 1]
                else:
                    res['response']['text'] = 'Хорошо, я верю в тебя, не подведи!'
            else:
                # иначе показываем следующую картинку
                res['response']['card'] = {}
                res['response']['card']['title'] = 'Неправильно. Хочешь, дам подсказку?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да, пожалуйста!',
                        'hide': True
                    },
                    {
                        'title': 'Не стоит, я попробую снова.',
                        'hide': True
                    }
                ]
                if "Да, пожалуйста!" in res['request']['nlu']['tokens']:
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['title'] = 'Это должно быть полезно:'
                    res['response']['card']['image_id'] = characters[character][attempt - 1]
                else:
                    res['response']['text'] = 'Хорошо, у тебя есть ещё две попытки!'
    # увеличиваем номер попытки для следующего шага
    sessionStorage[user_id]['attempt'] += 1


def get_character(req):
    # перебираем именованные сущности
    for entity in req['request']['nlu']['entities']:
        # если тип YANDEX.GEO, то пытаемся получить город(character), если нет, то возвращаем None
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value'].get('character', None)


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
