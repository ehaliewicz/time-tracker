from django.apps import AppConfig
import plotly.graph_objects as go
import logging

class StartupKaleido(AppConfig):
    name = 'todo'
    verbose_name = 'Todo Time Tracker'
    
    def ready(self):
        logging.critical("Initializing kaleido on startup...")
        fig = go.Figure(data=[go.Histogram(
            x=[0,1,2], y=[2,4,8],
        )])

        img_bytes = fig.to_image(format='svg')

        logging.critical("Done.")
        
        
