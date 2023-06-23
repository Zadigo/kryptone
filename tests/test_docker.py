import time
import redis
import logging


def simple_function():
    print('Started...')
    r = redis.Redis(host='redis', port=6379)
    while True:
        r.set('celebrity', 'Kendall')
        logging.info('Working')
        print('Working')
        time.sleep(5)


if __name__ == '__main__':
    try:
        simple_function()
    except KeyboardInterrupt:
        print('Stopped')
