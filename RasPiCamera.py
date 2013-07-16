import gdata.photos.service
import time, os, StringIO, subprocess
import ConfigParser
from PIL import Image

from subprocess import call
from datetime import datetime


# original code from 
# http://www.raspberrypi.org/phpBB3/viewtopic.php?p=358259#p362915


# Capture a small test image (for motion detection)
def captureTestImage():
    command = "raspistill -w %s -h %s -t 0 -e bmp -o -" % (100, 75)
    imageData = StringIO.StringIO()
    imageData.write(subprocess.check_output(command, shell=True))
    imageData.seek(0)
    im = Image.open(imageData)
    buffer = im.load()
    imageData.close()
    return im, buffer

# capture and upload a full size image to Picasa
def uploadImage(picasa, album_url):
    filename  = "/tmp/rpiTmp.jpg"
    call(["raspistill -rot 180 -w 2048 -o " + filename ], shell=True)
    photo = picasa.InsertPhotoSimple(album_url,'New Photo','',filename,content_type='image/jpeg')





def main():
    config = ConfigParser.ConfigParser()
    # read contents of config.ini from the same directory as the script itself
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.ini'))

    email    = config.get('LOGIN','email')
    password = config.get('LOGIN','password')
    username = config.get('LOGIN','username')

    album_name = config.get('CONFIG','album_name')
    loop_hrs = config.getint('CONFIG','hrs_to_loop')

    interval = config.getint('CONFIG','interval')
    # it takes 5-6 seconds to actually take a picture. Compensate for that
    if (interval >6 ):
        interval -= 6
    else:
        interval = 1
        
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
        
    #get an image to kick the process off with
    image1, buffer1 = captureTestImage()

    # Reset last capture time
    lastCapture = time.time()


    while (cur_time - start_time < loop_hrs):
        # Get comparison image
        image2, buffer2 = captureTestImage()
        
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
                lastCapture = time.time()
                uploadImage(picasa, album_url)
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
