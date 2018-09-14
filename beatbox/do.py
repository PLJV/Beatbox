class Do:
    def __init__(self, *args):
        """
        Do is a dictcomp interface for performing arbitrary spatial tasks with Vector and Raster objects
        :param args:
        """
        self._run = []
        self._what = []
        self._with = []
        try:
            self.run = args[0]
        except AttributeError:
            raise AttributeError("Failed to run action. Do assumes that the input is an attributed python "
                                 "dictionary. Is the object you passed something else?")

    @property
    def run(self):
        """
        Get method that will call our user-supplied run function
        :param args:
        :return:
        """
        return self._run(self._with)

    @run.setter
    def run(self, *args):
        """
        Set method for our run function. This specifies what we are going to do with our instance
        and does some object checks to determine an appropriate backend based on objects specified
        with the 'what' parameter. The setter will then call the function to perform the user
        specified action
        :param args:
        :return:
        """
        try:
            self._run = args[0]['run']
            self._what = args[0]['what']
            self._with = args[0]['with']
        except Exception as e:
            raise e
        # determine
        self._check_backend()
        # launch our run function
        return self.run

    def _check_backend(self, *args):
        """
        Parse the parameters specified by 'what' to determine whether this should run locally or on
        Earth Engine
        :param args:
        :return:
        """
        pass
