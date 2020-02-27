from gsm import GameObject, register_object
from gsm.mixins import Named
from gsm.common.world import grid
from gsm.common.elements import Card, Deck

# Buildings
register_object(game='catan', name='road', open={'loc', 'player'})
register_object(game='catan', name='settlement', open={'loc', 'player'})
register_object(game='catan', name='city', open={'loc', 'player'})

# Robber
register_object(game='catan', name='robber', open={'loc'})

# Dev
register_object(game='catan', name='devcard', cls=Card, req={'name', 'desc'})
register_object(game='catan', name='devdeck', cls=Deck)

# Game Board
register_object(game='catan', name='board', cls=grid.Grid)
register_object(game='catan', name='hex', cls=grid.Field)






