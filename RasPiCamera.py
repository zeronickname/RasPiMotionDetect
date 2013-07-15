import gdata.photos.service
import datetime
import ConfigParser


config = ConfigParser.ConfigParser()
config.read('login.ini')

email    = config.get('DEFAULT','email')
password = config.get('DEFAULT','password')
username = config.get('DEFAULT','username')
album_name = config.get('DEFAULT','album_name')
loop_hrs = config.get('DEFAULT','hrs_to_loop')

start_time = datetime.datetime.now().time().hour 
cur_time = datetime.datetime.now().time().hour


while (cur_time - start_time < loop_hrs):

    picasa = gdata.photos.service.PhotosService(email=email,password=password)
    picasa.ProgrammaticLogin()
    #album = picasa.InsertAlbum(title="Python Test", summary="test summary", access="private")

    albums = picasa.GetUserFeed(user=username)
    for album in albums.entry:
      if album.title.text==album_name:
        album_url = '/data/feed/api/user/default/albumid/%s' % (album.gphoto_id.text)

    filename  = "/home/gman/Development/gdata/MonkeyG.sketch.png"
    photo = picasa.InsertPhotoSimple(album_url,'New Photo','',filename,content_type='image/jpeg')
    
    cur_time = datetime.datetime.now().time().hour


