#!/usr/bin/python3

#各モジュールの読込み
import sys
import glob
import os
import re
import csv
import json
#PILモジュールからImageを読込み
from PIL import Image
Image.MAX_IMAGE_PIXELS = 10000000000

vipsbin = os.getcwd()+r'\vips-dev-w64-web-8.14.3\vips-dev-8.14\bin'
add_dll_dir = getattr(os, 'add_dll_directory', None)
if callable(add_dll_dir):
    add_dll_dir(vipsbin)
else:
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips


base_url = 'https://iiif.archive.waseda.jp/iiif/manifest/ktnsk/'
base_image_url = 'https://iiif.archive.waseda.jp/iiif/image/ktnsk/'
all_bib = {}
all_bib2 = {}
bib_title = []


def tiling_images(dir):
    sdir = 'sources/'+dir
    ifiles = glob.glob(sdir+'/*.jpg')
    if len(ifiles) == 0:
        ifiles = glob.glob(sdir+'/*.png')
    if len(ifiles) == 0:
        ifiles = glob.glob(sdir+'/*.tif')
    tiled_file_dir = 'iiifed/'+dir
    if not os.path.isdir(tiled_file_dir):
        os.makedirs(tiled_file_dir)    
    for ifile in ifiles:
        image = pyvips.Image.new_from_file(ifile, access='sequential')
        otfile = re.sub(r'sources/', 'iiifed/', os.path.splitext(ifile)[0])
        tfile = otfile+'.tif'
        if not os.path.isfile(otfile):
            print (tfile)
            image.tiffsave(tfile, tile=True, compression='jpeg', pyramid=True, tile_width=256, tile_height=256)
            os.rename(tfile, otfile)
            print (ifile+'を変換しました...')
        else:
            print (ifile+'はすでに存在します。')

    print ('\r\nピラミッドTIFFへの画像変換が終了しました！')



mani_keys = ['dir','label','Description'] 

#mani_keys = ['dir','title','license','attribution','within','logo','viewingHint','viewingDirection']
with open(sys.argv[1], newline='', encoding='utf_8_sig') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    rn = 0
    for row in spamreader:
        if rn == 0:
            bib_title = row
        else:
            each_bib = {}
            each_bib.update(zip(bib_title,row))
            link_name = row[0]  
            all_bib[link_name] = each_bib
        rn = rn + 1;     
#print (all_bib)

for key in all_bib.keys():
    each_manifest = {}
    all_meta = []
    file_dir0 = key
    tiling_images(key)
    glob_name = 'iiifed/'+key+'/*'
    #print (glob_name)
    if os.path.isdir('iiifed/'+key):
        list_file_names = glob.glob(glob_name)
        for item in all_bib[key]:
            if item not in mani_keys:
                each_meta  = {} 
                item_value = all_bib[key][item]
                each_meta['label'] = item
                each_meta['value'] = item_value
                all_meta.append(each_meta)
        each_manifest['@id'] = base_url+key+'/manifest.json'
        each_manifest['@type'] = 'sc:Manifest'
        #each_manifest['@context'] = 'http://iiif.io/api/presentation/2/context.json' 
        each_manifest['@context'] = 'http://iiif.io/api/presentation/3/context.json' 
        each_manifest['metadata'] = all_meta
        each_manifest['attribution'] = "早稲田大学図書館 (Waseda University Library)"
        each_manifest['license'] = "https://www.waseda.jp/library/user/using-images/"
        for mani_key in mani_keys:
            if all_bib[key].get(mani_key):
                if mani_key == 'label':
                    each_manifest['label'] = all_bib[key][mani_key]
                elif mani_key == 'viewingDirection':
                    each_manifest[mani_key] = all_bib[key][mani_key]
                elif mani_key == 'Description':
                    each_manifest['description'] = all_bib[key][mani_key]
        cn = 0
        sequence = {}
        canvases = []
        for file_path in list_file_names:
            service = {}
            resource = {}
            mani_image = {}
            canvas = {}
            file_dir_path_list = os.path.split(file_path)[0]
            file_dir = file_dir_path_list[0:len(file_dir_path_list)]
            file_path = re.sub(r'\\', '/', file_path)
            pr_file_path = re.sub(r'iiifed/', '', file_path)
            if os.path.isdir(file_dir):
              if not re.search('manifest.json', file_path):  
                cn = cn + 1
                canvas_number = 'p'+str(cn)+'.json'
                image_url_id = base_image_url+pr_file_path
                #20250916//presentation API 3 UPDATE
                #service['@context'] = 'http://iiif.io/api/image/2/context.json' 
                service['@context'] = 'http://iiif.io/api/image/3/context.json' 
                service['@id']  = image_url_id
                #Read the Image API Compliance document ("level[1-3]")
                #20250916//presentation API 3 UPDATE
                #service['profile'] = 'http://iiif.io/api/image/2/level1.json'
                service['profile'] = 'http://iiif.io/api/image/3/level1.json'
                img = Image.open(file_path)
                width, height = img.size
                resource['@type'] = 'dctypes:Image'
                resource['format'] = 'image/jpeg'
                resource['width'] = width
                resource['height'] = height
                resource['@id'] = image_url_id+'/full/full/0/default.jpg'
                resource['service'] = service
                mani_image['@type']  = 'oa:Annotation'
                mani_image['motivation']  = 'sc:painting'
                mani_image['resource']  = resource
                mani_image['@id']  = base_url+file_dir0+'/annotation/'+canvas_number
                mani_image['on']  = base_url+file_dir0+'/canvas/'+canvas_number
                canvas['label'] = 'p. '+str(cn)
                canvas['images'] = []
                canvas['images'].append(mani_image)
                canvas['width'] = width
                canvas['height'] = height
                canvas['@type'] = 'sc:Canvas'
                canvas['@id'] = base_url+file_dir0+'/canvas/'+canvas_number
                canvases.append(canvas)
        sequence['@id'] =  base_url+file_dir0+'/sequence/s1.json'
        sequence['@type'] =  'sc:Sequence'
        sequence['label'] =  'Current Page Order'
        sequence['canvases'] = canvases
        each_manifest['sequences'] = []
        each_manifest['sequences'].append(sequence)
        write_file_path = 'iiifed/'+file_dir0+'/manifest.json'
        print (write_file_path)
        with open(write_file_path, mode='w',encoding='utf_8') as f:
            json.dump(each_manifest, f, ensure_ascii=False,indent=2)
        print ('manifest.jsonの生成が終わりました。')
   
