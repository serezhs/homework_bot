import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(message)s',
    level=logging.INFO)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение отправлено')
    except Exception as error:
        logging.error(error)
        raise Exception('Не удалось отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}

    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)

        if api_answer.status_code != 200:
            raise Exception('Сбой при запросе к эндпоинту')

        return api_answer.json()

    except Exception as error:
        logging.error(error)
        raise Exception('Сбой при запросе к эндпоинту')


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks = response['homeworks']

        if type(homeworks) != list:
            raise KeyError(
                'Под ключом `homeworks` домашки приходят'
                'не в виде списка в ответ от API'
            )

        return homeworks

    except KeyError:
        logging.error(KeyError)
        raise KeyError('Отсутствуют ожидаемые ключи в ответе API')


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе
    статус этой работы
    """
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']

        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'

    except KeyError:
        logging.error(KeyError)
        raise KeyError('Недокументированный статус в ответе API')


def check_tokens():
    """
    Проверяет доступность переменных окружения,
    которые необходимы для работы программы
    """
    if TELEGRAM_TOKEN and PRACTICUM_TOKEN and TELEGRAM_CHAT_ID:
        a = True
    else:
        a = False
        logging.critical('Отсутствуют обязательные переменные')

    return a


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    set_errors = ['test_error']

    while True:
        try:
            check_tokens()
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            a = len(homeworks)
            if a > 0:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Новые статусы отстутсвуют')

            current_timestamp = response.get('current_date')
            if current_timestamp is None:
                error = 'Отсутствует ключ \'current_date\' в ответе API'
                logging.error(error)
                send_message(bot, error)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if set_errors[-1] != error:
                send_message(bot, message)
            set_errors.append(error)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
