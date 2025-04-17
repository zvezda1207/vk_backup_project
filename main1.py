import requests
import json
from tqdm import tqdm

from settings import service_access_token, y_token


class VK:
    def __init__(self, access_token, version=5.199):
        self.params = {
            'access_token': access_token,
            'v': version
        }
        self.base_url = 'https://api.vk.com/method/'

    def get_vk_photos(self, user_id, album_id='profile'):
        url = f'{self.base_url}photos.get'
        params = {
            'owner_id': user_id,
            'album_id': album_id,
            'extended': 1,
            'photo_sizes': 1,
        }
        params.update(self.params)

        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()['response']['items']


class YD:
    def __init__(self, token):
        self.token = token
        self.base_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        self.headers = {'Authorization': f'OAuth {token}'}

    def create_folder(self, folder_name):
        url = f'{self.base_url}?path={folder_name}'
        response = requests.put(url, headers=self.headers)
        response.raise_for_status()
        print(f'Папка "{folder_name}" успешно создана')
        return True

    def upload_file(self, file_path, image_content, overwrite=True):
        upload_url = f'{self.base_url}/upload?path={file_path}&overwrite={overwrite}'
        response = requests.get(upload_url, headers=self.headers)
        response.raise_for_status()
        upload_href = response.json().get('href')

        if not upload_href:
            print(f'Ошибка: не получен url для загрузки файла "{file_path}"')
            return False

        upload_response = requests.put(upload_href, headers={'Content-Type': 'image/jpeg'}, data=image_content)
        upload_response.raise_for_status()
        print(f'Файл "{file_path}" успешно загружен')
        return True


def main():
    user_id = input('Введите id пользователя VK: ')
    folder_name = 'vk_photos'

    vk = VK(access_token=service_access_token)
    yd = YD(token=y_token)

    photos = vk.get_vk_photos(user_id)
    if not photos:
        print('Не удалось получить фотографии из vk')
        return

    sorted_photos = sorted(photos, key=lambda x: max([size['width'] * size['height'] for size in x['sizes']]),
                           reverse=True)

    yd.create_folder(folder_name)

    uploaded_photos_info = []

    for photo in tqdm(sorted_photos[:5], desc='Загрузка фото на Яндекс.Диск'):
        max_size_url = None

        if 'sizes' in photo and photo['sizes']:
            available_sizes = [size for size in photo['sizes'] if
                               'width' in size and 'height' in size and size['width'] > 0 and size['height'] > 0]
            if available_sizes:
                max_size_url = max(available_sizes, key=lambda x: x['width'] * x['height'])['url']

        if not max_size_url:
            print(f'Нет доступного размера для фото "{photo["id"]}')
            continue

        response = requests.get(max_size_url)
        response.raise_for_status()
        image_content = response.content

        if 'likes' in photo and 'count' in photo['likes']:
            likes = photo['likes']['count']
        else:
            likes = 0

        file_name = f'{likes}.jpg'
        file_path = f'{folder_name}/{file_name}'

        if yd.upload_file(file_path, image_content):
            uploaded_photos_info.append({'file_name': file_name, 'size': max_size_url})

    with open('uploaded_photos.json', 'w', encoding='utf-8') as f:
        json.dump(uploaded_photos_info, f, ensure_ascii=False, indent=4)
        print('Фотографии успешно загружены на Яндекс.Диск и информация сохранена в "uploaded_photo.json"')

if __name__ == '__main__':
    main()

