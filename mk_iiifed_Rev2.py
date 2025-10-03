#!/usr/bin/python3

#各モジュールの読込み
import sys
import glob
import os
import re
import csv
import json
from PIL import Image
Image.MAX_IMAGE_PIXELS = 10000000000

#画像処理ライブラリ[pyvips]のDLLパス設定してモジュールを読込
#ローカルに[pivips]を展開し、そのbinディレクトリを指定
vipsbin = r'C:\work\waseda_IIIF\vips-dev-w64-web-8.17.2\vips-dev-8.17\bin'
os.environ['PATH'] = vipsbin + ';' + os.environ['PATH']
import pyvips

#IIIFマニフェストおよび画像サーバのベースURL定義
base_url = 'https://iiif.archive.waseda.jp/iiif/manifest/ktnsk/'
base_image_url = 'https://iiif.archive.waseda.jp/iiif/image/ktnsk/'
#dict型[all_bib]={請求番号:{metadata項目:値, ...}, ...},[bib_title]=[metadata項目, ...]
all_bib = {}
bib_title = []

#tiling_images関数で指定ディレクトリ内の画像ファイルをピラミッドTIFFに変換
#予め[sources]ディレクトリを作成し、その配下に各画像セット用のサブディレクトリと末端に画像ファイルを配置
def tiling_images(dir):
    sdir = 'sources/' + dir
    ifiles = glob.glob(sdir + '/*.jpg')
    if len(ifiles) == 0:
        ifiles = glob.glob(sdir + '/*.png')
    if len(ifiles) == 0:
        ifiles = glob.glob(sdir + '/*.tif')
    tiled_file_dir = 'iiifed/' + dir
    if not os.path.isdir(tiled_file_dir):
        os.makedirs(tiled_file_dir)
    for ifile in ifiles:
        image = pyvips.Image.new_from_file(ifile, access='sequential')
        otfile = re.sub(r'sources/', 'iiifed/', os.path.splitext(ifile)[0])
        tfile = otfile + '.tif'
        if not os.path.isfile(otfile):
            print(tfile)
            image.tiffsave(tfile, tile=True, compression='jpeg', pyramid=True, tile_width=256, tile_height=256)
            os.rename(tfile, otfile)
            print(ifile + 'を変換しました...')
        else:
            print(ifile + 'はすでに存在します。')
    print('\r\nピラミッドTIFFへの画像変換が終了しました！')

#マニフェストに追加するメタデータをCSVファイルから読み込む。各行をRDB形式で記載しておく
mani_keys = ['dir', 'title', 'license', 'attribution', 'within', 'logo', 'viewingHint', 'viewingDirection']

#各請求番号ディレクトリごとに画像ファイルを走査
#metadataの項目と値を[each_bib]に格納し、[all_bib]に追加して、1レコードずつデータを格納
with open(sys.argv[1], newline='', encoding='utf_8_sig') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    rn = 0
    for row in spamreader:
        if rn == 0:
            bib_title = row
        else:
            each_bib = {}
            each_bib.update(zip(bib_title, row))
            link_name = row[0]
            all_bib[link_name] = each_bib
        rn += 1

#IIIFマニフェスト生成処理
for key in all_bib.keys():
    manifest = {}
    metadata = []
    file_dir0 = key
    tiling_images(key)
    glob_name = 'iiifed/' + key + '/*'
    if os.path.isdir('iiifed/' + key):
        list_file_names = glob.glob(glob_name)
        # メタデータ追加処理
        for item in all_bib[key]:
            if item not in mani_keys:
                item_value = all_bib[key][item]
                metadata.append({
                    "label": {"ja": [item]},
                    "value": {"ja": [item_value]}
                })
            manifest['@context'] = 'http://iiif.io/api/presentation/3/context.json'
            manifest['id'] = base_url + key + '/manifest.json'
            manifest['type'] = 'Manifest'
            manifest['label'] = {"ja": [all_bib[key].get('title', key)]}
            manifest['metadata'] = metadata
            manifest['attribution'] = {"ja": ["早稲田大学図書館"],
                                       "en": ["Waseda University Library"]}
            manifest['license'] = "https://www.waseda.jp/library/user/using-images/"
            #ロゴイメージ
            manifest['logo'] = {"id": "https://www.wul.waseda.ac.jp/kotenseki/img/mark.gif",
                                "type": "Image"}
            #"viewingDirection" [left-to-right](the default if the property is not specified),[right-to-left],[top-to-bottom],[bottom-to-top]
            if all_bib[key].get('viewingDirection'):
                manifest['viewingDirection'] = all_bib[key]['viewingDirection']
            # Canvas配列
            items = []
            cn = 0
            for file_path in list_file_names:
                file_path = re.sub(r'\\', '/', file_path)
                pr_file_path = re.sub(r'iiifed/', '', file_path)
            #画像ファイルをCanvasとしてマニフェストに追加処理
            if not re.search('manifest.json', file_path):
                cn += 1
                canvas_number = 'p' + str(cn) + '.json'
                image_url_id = base_image_url + pr_file_path
                img = Image.open(file_path)
                width, height = img.size
                #Canvas情報の作成
                canvas_id = base_url + file_dir0 + '/canvas/' + canvas_number
                canvas = {
                    "id": canvas_id,
                    "type": "Canvas",
                    "label": {"ja": [f"p. {cn}"]},
                    "width": width,
                    "height": height,
                    "items": []
                }
                #AnnotationPage情報の作成
                annotation_page_id = canvas_id + '/annotationpage'
                annotation_page = {
                    "id": annotation_page_id,
                    "type": "AnnotationPage",
                    "items": []
                }
                #Annotation情報の作成
                annotation_id = canvas_id + '/annotation'
                annotation = {
                    "id": annotation_id,
                    "type": "Annotation",
                    "motivation": "painting",
                    "body": {
                        "id": image_url_id + '/full/full/0/default.jpg',
                        "type": "Image",
                        "format": "image/jpeg",
                        "width": width,
                        "height": height,
                        #Rev: "tiles"プロパティ追加
                        "tiles" : [
                            {"width": 256, "scaleFactors": [1, 2, 4]},
                            {"width": 512, "scaleFactors": [8, 16]}
                        ],
                        "service": [{
                            "id": image_url_id,
                            "type": "ImageService3",
                            "profile": "level1",
                            "width": width,
                            "height": height
                        }]
                    },
                    "target": canvas_id
                }
                #生成したannotationをannotation_pageに、annotation_pageをcanvasに追加
                annotation_page["items"].append(annotation)
                canvas["items"].append(annotation_page)
                items.append(canvas)
        #manifestにCanvas配列を追加して、JSONファイルとして保存
        manifest["items"] = items
        #書き出しファイルパスの作成とJSONファイルの保存
        write_file_path = 'iiifed/' + file_dir0 + '/manifest.json'
        print(write_file_path) 
        with open(write_file_path, mode='w', encoding='utf_8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print('manifest.jsonの生成が終わりました。')
