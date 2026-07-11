import os
import re
import pandas as pd
'''
Update seasons combined dataset by:
1. downloading current year data
2. removing data from current year in combined dataset
3. replacing data with current year dataset
'''
class UpdateCombinedDataset:
    def __init__(self,dataset_file:str):
        dataset_file = dataset_file
        df = loadDataset()
        deletedRecords= False


        

    def loadDataset(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.dataset_file)
            return df
        except FileNotFoundError:
            print(f"File not found: {self.dataset_file}")
            return None
            #add conditional later to not run update if data = None
        

    def deleteYearRecords(self,year=int)->bool:
        '''
        Takes a given year and removes all records from that year in the combined dataset
        parameter: year (int)
        '''
        try:
            self.df = self.df[self.df['season'] != year]
            self.deletedRecords = True
            return self.deletedRecords
        except OSError:
            print("Dataframe operation incomplete")
            self.deletedRecords = False
            return self.deletedRecords
        



        