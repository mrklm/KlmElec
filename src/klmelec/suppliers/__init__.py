"""Ajouter un connecteur ici ne modifie ni le catalogue ni les calculs."""
from .elec123 import Elec123
from .elec_distrib import ElecDistrib

CONNECTORS = {'123elec': Elec123(), 'elecdistrib': ElecDistrib()}
