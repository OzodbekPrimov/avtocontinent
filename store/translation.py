from modeltranslation.translator import translator, TranslationOptions
from .models import Category, Brand, CarModel, Product, Banner

class BaseTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'short_description', 'meta_title', 'meta_description')

class BannerTranslationOptions(TranslationOptions):
    fields = ('title',)

translator.register(Category, BaseTranslationOptions)
translator.register(Brand, BaseTranslationOptions)
translator.register(CarModel, BaseTranslationOptions)
translator.register(Product, ProductTranslationOptions)
translator.register(Banner, BannerTranslationOptions)
