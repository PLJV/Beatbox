### Scripts
The scripts path contains standalone python scripts that can be called from a shell to perform common GIS tasks. You can also import the scripts on the client-side for integration into your own workflows.

### Quickstart
##### From BASH:
```bash
python moving_windows.py -r nass_2016.tif -reclass row_crop=1,2,3 wheat=2,7 -mw 3,11,33 -function numpy.sum
```
