class Do:
    def __init__(self, *args):
        """ do is a dictcomp interface for performing arbitrary spatial
        tasks with Vector and Raster objects"""
        self._run = {}
        self._what = {}
        self._with = {}

        self.run = args[0]

    @property
    def run(self, *args):
        return self._run(self._with)

    @run.setter
    def run(self, *args):
        try:
            self._run = args[0]['run']
            self._what = args[0]['what']
            self._with = args[0]['with']
        except Exception as e:
            raise e
