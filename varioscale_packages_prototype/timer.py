import time


class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start


class MeasureTime(object):
    def __init__(self):
        self.measures = {}
    
    def measure(self, name):
        t = time.time()
        start_nm = name + "_start"
        end_nm = name + "_end"
        if start_nm in self.measures:
            assert end_nm not in self.measures
            self.measures[end_nm] = t
        else: 
            self.measures[start_nm] = t

    def duration(self, name):
        start_nm = name + "_start"
        end_nm = name + "_end"
        assert start_nm in self.measures, start_nm
        assert end_nm in self.measures, end_nm
        return self.measures[end_nm] - self.measures[start_nm]