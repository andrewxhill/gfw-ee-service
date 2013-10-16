"""One-line documentation for biomass module.

A detailed description of biomass.
"""

import os
import ee
import webapp2
import jinja2
import httplib2
from oauth2client.appengine import AppAssertionCredentials
from google.appengine.api import memcache
import urllib
from google.appengine.api import urlfetch

jinja_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

#Global variables
EE_URL = 'https://earthengine.googleapis.com'

# The OAuth scope URL for the Google Earth Engine API.
GEE_SCOPE = 'https://www.googleapis.com/auth/earthengine.readonly'
SCOPES = (GEE_SCOPE)
credentials = AppAssertionCredentials(scope=SCOPES)

class MainPage(webapp2.RequestHandler):
    def get(self):

      ee.Initialize(credentials, EE_URL)
      mapid = ee.Image('srtm90_v4').getMapId({'min':0, 'max':1000})


      template_values = {
          'mapid' : mapid['mapid'],
          'token' : mapid['token']
          }
      template = jinja_environment.get_template('index.html')
      self.response.out.write(template.render(template_values))


class MapInit():
  def __init__(self,reqid):
      self.mapid = memcache.get(reqid)
      cache_time = 2
      if self.mapid is None:
        ee.Initialize(credentials, EE_URL)
        if reqid == 'l7_toa_1year_2012':
          # The Green Forest Coverage background created by Andrew Hill
          # example here: http://ee-api.appspot.com/#331746de9233cf1ee6a4afd043b1dd8f
          satellite = ee.Image("L7_TOA_1YEAR_2012")
          self.mapid = satellite.getMapId({'opacity': 1, 'bands':'30,20,10', 'min':10, 'max':120, 'gamma':"1.6"});
        
        if reqid == 'simple_green_coverage':
          # The Green Forest Coverage background created by Andrew Hill
          # example here: http://ee-api.appspot.com/#331746de9233cf1ee6a4afd043b1dd8f
          treeHeight = ee.Image("Simard_Pinto_3DGlobalVeg_JGR")
          elev = ee.Image('srtm90_v4')
          mask2 = elev.gt(0).add(treeHeight.mask())
          water = ee.Image("MOD44W/MOD44W_005_2000_02_24").select(["water_mask"]).eq(0)
          self.mapid = treeHeight.mask(mask2).mask(water).getMapId({'opacity': 1, 'min':0, 'max':50, 'palette':"dddddd,1b9567,333333"});
          

        if reqid == 'simple_bw_coverage':
          # The Green Forest Coverage background created by Andrew Hill
          # example here: http://ee-api.appspot.com/#331746de9233cf1ee6a4afd043b1dd8f
          treeHeight = ee.Image("Simard_Pinto_3DGlobalVeg_JGR")
          elev = ee.Image('srtm90_v4')
          mask2 = elev.gt(0).add(treeHeight.mask())
          self.mapid = treeHeight.mask(mask2).getMapId({'opacity': 1, 'min':0, 'max':50, 'palette':"ffffff,777777,000000"});
        
        memcache.set(reqid,self.mapid,cache_time)
        # elif reqid == 'dark_tree_height':
        #   # The Dark Forest Height background created by Andrew Hill
        #   ee.Initialize(credentials, EE_URL)
        #   treeHeight = ee.Image("Simard_Pinto_3DGlobalVeg_JGR")
        #   elev = ee.Image('srtm90_v4')
        #   mask2 = elev.gt(0).add(treeHeight.mask())
        #   # addToMap(treeHeight, {opacity: 0.68, min:0, max:0, palette:"171717"}, "Water");
        #   self.mapid = treeHeight.mask(mask2).getMapId({'opacity': 0.98, 'min':0, 'max':50, 'palette':"aaaaaa,1b9567,333333"})
        #   memcache.set(reqid,self.mapid,9000)



# Depricated method, GFW will move to KeysGFW and not deliver tiles from the proxy directly
class TilesGFW(webapp2.RequestHandler):
    def get(self, m, z, x, y):

      mapid = MapInit(m.lower()).mapid

      if mapid is None:
        # TODO add better error code control
        self.error(500)
      else:
        
        cached_image = memcache.get("%s-tile-%s-%s-%s" % (m,z,x,y))

        if cached_image is None:
          result = urlfetch.fetch(url="https://earthengine.googleapis.com/map/%s/%s/%s/%s?token=%s" % (mapid['mapid'], z, x, y, mapid['token']))
          if result.status_code == 200:
            memcache.set("%s-tile-%s-%s-%s" % (m,z,x,y),result.content,90000)
            self.response.headers["Content-Type"] = "image/png"
            self.response.headers.add_header("Expires", "Thu, 01 Dec 1994 16:00:00 GMT")
            self.response.out.write(result.content)
          else:
            self.response.set_status(result.status_code)
        else:
          self.response.headers["Content-Type"] = "image/png"
          self.response.headers.add_header("Expires", "Thu, 01 Dec 1994 16:00:00 GMT")
          self.response.out.write(cached_image)


class KeysGFW(webapp2.RequestHandler):
    def get(self, m, z, x, y):

      mapid = MapInit(m.lower()).mapid

      if mapid is None:
        # TODO add better error code control
        self.error(500)
      else:
        self.response.header['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(['key', mapid]))


app = webapp2.WSGIApplication([ 
    ('/', MainPage), 
    ('/gfw/([^/]+)/([^/]+)/([^/]+)/([^/]+).png', TilesGFW), 
    ('/gfw/([^/]+)', KeysGFW)

  ], debug=True)


