# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from os.path import getsize, islink
from screener.database import session, Category, Image

def category_disk_space(request, category):
    category = Category.query.get(category)
    if not category:
        return dict(status=1, msg="Category not found")

    images = resized = thumbs = abuse = 0
    for image in category.images:
        if image.abuse:
            abuse += getsize(image.image_path) + getsize(image.thumb_path)
            if not islink(image.resized_path):
                abuse += getsize(image.resized_path)
        else:
            images += getsize(image.image_path)
            thumbs += getsize(image.thumb_path)
            if not islink(image.resized_path):
                resized += getsize(image.resized_path)

    return dict(
        status=0,
        images=images,
        thumbs=thumbs,
        resized=resized,
        abuse=abuse
    )


