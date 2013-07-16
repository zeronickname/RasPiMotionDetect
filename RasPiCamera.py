import gdata.photos.service
import datetime, time, os, StringIO, subprocess
import ConfigParser
from PIL import Image

from subprocess import call
from datetime import datetime


config = ConfigParser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.ini'))

email    = config.get('LOGIN','email')
password = config.get('LOGIN','password')
username = config.get('LOGIN','username')

album_name = config.get('CONFIG','album_name')
loop_hrs = config.getint('CONFIG','hrs_to_loop')
interval = config.getint('CONFIG','interval')
threshold = config.getint('CONFIG','picture_threshold')
sensitivity = config.getint('CONFIG','picture_sensitivity')

# it takes 5-6 seconds to actually take a picture. Compensate for that
if (interval >6 ):
    interval -= 6


start_time = datetime.datetime.now().time().hour 
cur_time = datetime.datetime.now().time().hour


picasa = gdata.photos.service.PhotosService(email=email,password=password)
picasa.ProgrammaticLogin()
#album = picasa.InsertAlbum(title="Python Test", summary="test summary", access="private")

albums = picasa.GetUserFeed(user=username)
for album in albums.entry:
  if album.title.text==album_name:
    album_url = '/data/feed/api/user/default/albumid/%s' % (album.gphoto_id.text)
    
filename  = "/tmp/rpiTmp.jpg"

while (cur_time - start_time < loop_hrs):
    call(["raspistill -rot 180 -w 2048 -o " + filename ], shell=True)
    photo = picasa.InsertPhotoSimple(album_url,'New Photo','',filename,content_type='image/jpeg')
    cur_time = datetime.datetime.now().time().hour
    time.sleep(interval)


