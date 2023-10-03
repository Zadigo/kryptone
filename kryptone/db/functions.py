def validate_images(images):
    def filter_function(image):
        return image.startswith('http')
    return list(filter(filter_function, images))
