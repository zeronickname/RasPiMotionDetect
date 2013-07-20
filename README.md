Intro
======================

No matter what the project title says, this is *not* an intervalometer :)
It started off as one (check the history), but I pretty quickly came to the conclusion that without motion detection, a naive implementation of an intervalometer is kindof useless. You just wind up with either a lot of pictures, or you miss the really important ones.

So, this script now has some configurable parameters to tweak the motion sensitivity and as long as there is movement, it takes and uploads pics continuously to Picasa/Google Plus Photos.

Picasa was chosen as an endpoint because photos <5Mpx do not count towards your storage.
Plus google kindly stitches together similair photos to create an animated gif, which is pretty awesome!

PreRequisites:
======================


* Python 2.x
* PIL
    sudo apt-get install python-imaging
* gdata-python-client
    Download and install from: https://developers.google.com/gdata/articles/python_client_lib#library

