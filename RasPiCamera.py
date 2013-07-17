# original motion detection code from 
# http://www.raspberrypi.org/phpBB3/viewtopic.php?p=358259#p362915


import gdata.photos.service
import time, os, StringIO, subprocess
import ConfigParser
from PIL import Image
import threading, Queue

from subprocess import call
from datetime import datetime


class background_upload(threading.Thread):
    def __init__ (self, picasa, album_url, q):
        self.picasa = picasa
        self.album_url = album_url
        self.q = q
        threading.Thread.__init__ (self)
        self.daemon = True
   
    def run(self):
        while True:
            filename = self.q.get()
            photo = self.picasa.InsertPhotoSimple(self.album_url,'New Photo','',filename,content_type='image/jpeg')


# Capture a small test image (for motion detection)
def captureTestImage():
    command = "raspistill -rot 180 -w %s -h %s -t 0 -e bmp -o -" % (100, 75)
    imageData = StringIO.StringIO()
    imageData.write(subprocess.check_output(command, shell=True))
    imageData.seek(0)
    im = Image.open(imageData)
    buffer = im.load()
    return im, buffer, imageData

# capture and upload a full size image to Picasa
def uploadImage(queue):
    command = "raspistill -rot 180 -w 2048 -o -"
    imageData = StringIO.StringIO()
    imageData.write(subprocess.check_output(command, shell=True))
    imageData.seek(0)
    queue.put(imageData)


def main():
    config = ConfigParser.ConfigParser()
    # read contents of config.ini from the same directory as the script itself
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.ini'))

    email    = config.get('LOGIN','email')
    password = config.get('LOGIN','password')
    username = config.get('LOGIN','username')

    album_name = config.get('CONFIG','album_name')
    loop_hrs = config.getint('CONFIG','hrs_to_loop')

    # currently unused. Maybe useful at come later point.
    interval = config.getint('CONFIG','interval')
        
    threshold = config.getint('CONFIG','picture_threshold')
    sensitivity = config.getint('CONFIG','picture_sensitivity')
    forceCaptureTime = config.getint('CONFIG','forceCaptureTime')


    start_time = datetime.now().time().hour 
    cur_time = datetime.now().time().hour

    picasa = gdata.photos.service.PhotosService(email=email,password=password)
    picasa.ProgrammaticLogin()
    #album = picasa.InsertAlbum(title="Python Test", summary="test summary", access="private")

    albums = picasa.GetUserFeed(user=username)
       
    for album in albums.entry:
      if album.title.text==album_name:
        album_url = '/data/feed/api/user/default/albumid/%s' % (album.gphoto_id.text)
    
    upload_queue = Queue.Queue()
    uploadThread = background_upload(picasa, album_url, upload_queue)
    uploadThread.start()
    
        
    #get an image to kick the process off with
    image1, buffer1, imd = captureTestImage()

    # Reset last capture time
    lastCapture = time.time()


    while (cur_time - start_time < loop_hrs):
        # Get comparison image
        image2, buffer2, imd = captureTestImage()
        
        # Count changed pixels
        changedPixels = 0
        for x in xrange(0, 100):
            # Scan one line of image then check sensitivity for movement
            for y in xrange(0, 75):
                # Just check green channel as it's the highest quality channel
                pixdiff = abs(buffer1[x,y][1] - buffer2[x,y][1])
                if pixdiff > threshold:
                    changedPixels += 1

            # If movement sensitivity exceeded, upload image and
            # Exit before full image scan complete
            if changedPixels > sensitivity:
                # the test image is quite low res, but we might as well upload it
                upload_queue.put(imd)
                lastCapture = time.time()
                uploadImage(upload_queue)
                break
            continue    
        
        # Check force capture
        if time.time() - lastCapture > forceCaptureTime:
            changedPixels = sensitivity + 1            

        # Swap comparison buffers
        image1  = image2
        buffer1 = buffer2
        
        cur_time = datetime.now().time().hour


if __name__ == '__main__':
    main()
