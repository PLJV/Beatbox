from osgeo import ogr

import os

class Shapefile:

    def __init__(self, *args):

        self.data_source = None
        self.layer = None
        self.definition = None

        self.is_valid = False # Does shapefile contain valid fields?

        if args:
            if(os.path.exists(args[0])):
                self.open(args[0])

    def open(self, path, layer=0):
        """
        Attempts to read-in a standard shapefile using OGR
        """
        try:
            self.data_source = ogr.Open(path)
            self.layer = self.data_source.GetLayer(layer)
            self.definition = self.layer.GetLayerDefn()
        except Exception as e:
            print(e)

    def check_restoration_features(self):
        """
        sanity-checks the contents of the attribute table to ensure consistency
        with calc_restore_cost
        """
        req_playa_fields = ['hydromod','farmed']
        field_match = 0
        try:
            fields = []
            for i in range(self.definition.GetFieldCount()):
                fields.append(self.definition.GetFieldDefn(i).GetName())
        except Exception as e:
            print(e)

        for i in range(len(req_playa_fields)):
            if req_playa_fields[i] in fields:
                field_match += 1

        self.is_valid = (field_match == 3)


class CalulateRestoreCost:
    """
    Calculate Restore Cost Factory
    Will allow individual implementations of calc appropriate for a series of conservation actions.
    """
    def __init__(self):
        pass

    def calc(self):
        pass


class CalculateRestoreCostTabular:
    """Calculate restoration costs for a playa, given modifications. This is a non-spatial implementation."""
    def __init__(self, hydromod, farmed, playaacres):
        #unit conversions
        m2pa = 4046.86
        cypacreft = 1613.34

        playaradiusm = math.sqrt((playaacres * m2pa)/math.pi)
        bufferacres = (80*playaradiusm + 1600)/m2pa

        return (hydromod * cost_pit) + (farmed * bufferacres * cost_bufferpa) \
            + (farmed * playaacres * cypacreft * cost_sedimentpcy)

class CalculateRestoreCostShapefile:
    """Calculate restoration costs for a playa, given modifications. This is a spatial implementation."""
    def __init__(self, shapes):
        pass
        
if __name__ == "__main__":

    s = Shapefile("myShapefile.shp")
    s.check_restoration_features()

    if s.is_valid:
        for feature in s.layer:
            args = [ feature.GetField['hydromod'], feature.GetField['farmed'] ]
            args.append(feature.GetGeometryRef().GetArea())
            print(calc_restore_cost(hydromod=args[0],farmed=args[1],playaacres=args[2]))
