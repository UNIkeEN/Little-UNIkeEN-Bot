from .basicConfigs import BACKEND, BACKEND_TYPE

if BACKEND == BACKEND_TYPE.GOCQHTTP:
    from .basicEventForGocqhttp import *
elif BACKEND == BACKEND_TYPE.LAGRANGE:
    from .basicEventForLagrange import *
