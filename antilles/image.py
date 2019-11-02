import warnings

import numpy
import openslide
import wx

from antilles.io import DAO


def get_screen_size():
    app = wx.App(False)
    size = wx.GetDisplaySize()
    del app

    return size


screen_size = get_screen_size()


def get_slide_dims(path):
    with openslide.OpenSlide(DAO.abs(path)) as obj:
        return obj.dimensions


def openslide_mpp(obj):
    mpp_x = float(obj.properties[openslide.PROPERTY_NAME_MPP_X])
    mpp_y = float(obj.properties[openslide.PROPERTY_NAME_MPP_Y])

    if not numpy.equal(mpp_x, mpp_y):
        warnings.warn(
            'MPP values are not equal in x and y directions! '
            'x: {x}, y: {y}'.format(x=mpp_x, y=mpp_y))
        mpp = numpy.average((mpp_x, mpp_y))

    else:
        mpp = mpp_x

    return mpp


def calc_downsample_factor(dims):
    w, h = dims
    return int(max(float(w) / float(screen_size[0]),
                   float(h) / float(screen_size[1])))


def downsample(path):
    with openslide.OpenSlide(DAO.abs(path)) as obj:
        dims = obj.dimensions
        factor = calc_downsample_factor(dims)

        dims_tn = tuple(int(float(s) / float(factor)) for s in dims)
        image = obj.get_thumbnail(dims_tn)

    return {'factor': factor,
            'image': image}
