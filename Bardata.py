import pandas as pd
import numpy as np

class BarData():
    def __init__(self,**kwargs) -> None:

        for key,value in kwargs.items():
            setattr(self,key,value)
        
        return