from django.conf import settings
from modeltranslation.forms import TranslationModelForm
from django import forms
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from store.models import CarModel, Category, Product, Order, PaymentSettings, ExchangeRate, Brand, \
    Banner
from django.core.exceptions import ValidationError


class ProductForm(forms.ModelForm):
    """
    Product model uchun forma.
    ModelTranslation bilan name va description maydonlari har bir til uchun avtomatik yaratiladi.
    """

    # Majburiy bo'lgan tarjima maydonlari
    name_uz = forms.CharField(
        max_length=200,
        required=True,
        label="Nomi (O'zbek)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Mahsulot nomini kiriting"
        })
    )

    name_en = forms.CharField(
        max_length=200,
        required=True,
        label="Name (English)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Enter product name"
        })
    )

    name_ru = forms.CharField(
        max_length=200,
        required=True,
        label="Название (Русский)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Введите название продукта"
        })
    )

    # Description maydonlari (RichTextField uchun widget)
    description_uz = forms.CharField(
        required=True,
        label="Tavsifi (O'zbek)",
        widget=forms.Textarea(attrs={
            'class': 'form-control rich-text-editor',
            'rows': 6,
            'placeholder': "Mahsulot tavsifini kiriting"
        })
    )

    description_en = forms.CharField(
        required=True,
        label="Description (English)",
        widget=forms.Textarea(attrs={
            'class': 'form-control rich-text-editor',
            'rows': 6,
            'placeholder': "Enter product description"
        })
    )

    description_ru = forms.CharField(
        required=True,
        label="Описание (Русский)",
        widget=forms.Textarea(attrs={
            'class': 'form-control rich-text-editor',
            'rows': 6,
            'placeholder': "Введите описание продукта"
        })
    )

    # Short description (ixtiyoriy)
    short_description = forms.CharField(
        max_length=500,
        required=False,
        label="Qisqa tavsif",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': "Qisqa tavsif (ixtiyoriy)"
        })
    )

    # SKU maydoni
    sku = forms.CharField(
        max_length=100,
        required=True,
        label="SKU",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Mahsulot SKU kodini kiriting"
        })
    )

    # Slug maydoni
    slug = forms.CharField(
        max_length=200,
        required=False,
        label="Slug",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Avtomatik yaratiladi",
            'readonly': True
        }),
        help_text="URL uchun ishlatiladigan qisqa nom"
    )

    # Category
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=True,
        label="Kategoriya",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_category'
        })
    )

    # Compatible models
    compatible_models = forms.ModelMultipleChoiceField(
        queryset=CarModel.objects.all(),
        required=True,
        label="Mos avtomobil modellari",
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )

    # Price
    price_usd = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        label="Narxi (USD)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': "0.00"
        })
    )

    # Stock quantity
    stock_quantity = forms.IntegerField(
        min_value=0,
        required=True,
        label="Ombordagi miqdori",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': "0"
        })
    )

    # Main image
    main_image = forms.ImageField(
        required=True,
        label="Asosiy rasm",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    # YouTube video (ixtiyoriy)
    youtube_video_id = forms.CharField(
        max_length=50,
        required=False,
        label="YouTube video ID",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Masalan: jL14SRWKA6c"
        }),
        help_text="YouTube video ID (ixtiyoriy)"
    )

    # Status fields
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Faol",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    is_featured = forms.BooleanField(
        required=False,
        initial=False,
        label="Tavsiya etiladi",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = Product
        fields = [
            'name_uz', 'name_en', 'name_ru',
            'description_uz', 'description_en', 'description_ru',
            'short_description', 'sku', 'slug', 'category',
            'compatible_models', 'price_usd', 'stock_quantity',
            'main_image', 'youtube_video_id', 'is_active', 'is_featured'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_sku(self):
        """SKU ni tekshirish"""
        sku = self.cleaned_data.get('sku')
        if sku:
            # Mavjud mahsulotlardan tashqari, boshqa mahsulotlarda bu SKU bor yoki yo'qligini tekshirish
            existing = Product.objects.filter(sku=sku)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError("Bu SKU kodi allaqachon mavjud.")

        return sku

    def clean_name_uz(self):
        """O'zbek tilida nom tekshirish"""
        name_uz = self.cleaned_data.get('name_uz')
        if not name_uz or not name_uz.strip():
            raise ValidationError("O'zbek tilida nom kiritilishi shart.")
        return name_uz.strip()

    def clean_description_uz(self):
        """O'zbek tilida tavsif tekshirish"""
        description_uz = self.cleaned_data.get('description_uz')
        if not description_uz or not description_uz.strip():
            raise ValidationError("O'zbek tilida tavsif kiritilishi shart.")
        return description_uz.strip()

    def clean_youtube_video_id(self):
        """YouTube video ID ni tekshirish"""
        video_id = self.cleaned_data.get('youtube_video_id')
        if video_id:
            # YouTube video ID format tekshirish (11 ta belgi)
            if len(video_id) != 11:
                raise ValidationError("YouTube video ID 11 ta belgidan iborat bo'lishi kerak.")
        return video_id

    def clean(self):
        """Forma ma'lumotlarini tozalash va tekshirish"""
        cleaned_data = super().clean()
        
        # Slug ni avtomatik yaratish agar bo'sh bo'lsa
        if not cleaned_data.get('slug') and cleaned_data.get('name_uz'):
            base_slug = slugify(cleaned_data['name_uz'])
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.instance.pk if self.instance else None).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            cleaned_data['slug'] = slug
        
        return cleaned_data

    def save(self, commit=True):
        """Mahsulotni saqlash va slug yaratish"""
        instance = super().save(commit=False)

        # name_uz asosida slug yaratish
        if self.cleaned_data.get('name_uz'):
            base_slug = slugify(self.cleaned_data['name_uz'])
            if not base_slug:
                # Agar slugify natija bermasa, transliteration yoki boshqa usul ishlatish
                base_slug = slugify(self.cleaned_data['name_uz'], allow_unicode=True)

            # Unique slug yaratish
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            instance.slug = slug

        if commit:
            instance.save()
            # ManyToMany maydonlarni saqlash
            self.save_m2m()

        return instance


from django import forms
from django.core.exceptions import ValidationError



class BannerForm(forms.ModelForm):
    # Model fieldlar bilan mos kelmaydigan fieldlar uchun alohida fieldlar
    title_uz = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "O'zbekcha sarlavha kiriting (ixtiyoriy)"
        })
    )
    title_ru = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Ruscha sarlavha kiriting (ixtiyoriy)"
        })
    )
    title_en = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Inglizcha sarlavha kiriting (ixtiyoriy)"
        })
    )

    class Meta:
        model = Banner
        fields = ['image', 'link', 'is_active', 'order']
        widgets = {
            'link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': "https://misol.com (ixtiyoriy)"
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Faqat image va order majburiy
        self.fields['image'].required = True
        self.fields['order'].required = True

        # Boshqa maydonlar ixtiyoriy
        self.fields['link'].required = False
        self.fields['is_active'].required = False

        # Label va placeholderlarni tilga moslashtirish
        self.fields['title_uz'].label = "Sarlavha (Oʻzbekcha)"
        self.fields['title_ru'].label = "Заголовок (Русский)"
        self.fields['title_en'].label = "Title (English)"
        self.fields['link'].label = "Havola URL"
        self.fields['order'].label = "Tartib"
        self.fields['is_active'].label = "Faol holati"
        self.fields['image'].label = "Banner rasmi"

        # Agar object mavjud bo'lsa, title maydonlarini to'ldirish
        if self.instance and self.instance.pk and hasattr(self.instance, 'title'):
            # Bitta title maydonidan barcha til maydonlarini to'ldirish
            self.fields['title_uz'].initial = self.instance.title
            self.fields['title_ru'].initial = self.instance.title
            self.fields['title_en'].initial = self.instance.title

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise ValidationError("Rasm yuklash majburiy!")

        # Rasm hajmini tekshirish (5MB)
        if hasattr(image, 'size') and image.size > 5 * 1024 * 1024:
            raise ValidationError("Rasm hajmi 5MB dan oshmasligi kerak!")

        # Rasm formatini tekshirish
        if hasattr(image, 'name'):
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            ext = image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError(f"Faqat {', '.join(valid_extensions)} formatdagi rasmlar qabul qilinadi!")

        return image

    def clean_order(self):
        order = self.cleaned_data.get('order')
        if order is None:
            raise ValidationError("Tartib raqami majburiy!")

        if order < 1:
            raise ValidationError("Tartib raqami 1 dan kichik bo'lmasligi kerak!")

        return order

    def clean_link(self):
        link = self.cleaned_data.get('link')
        if link and not (link.startswith('http://') or link.startswith('https://')):
            raise ValidationError("Havola http:// yoki https:// bilan boshlanishi kerak!")
        return link or ''

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Title maydonlaridan birontasini tanlash yoki birlashtirib saqlash
        title_uz = self.cleaned_data.get('title_uz', '').strip()
        title_ru = self.cleaned_data.get('title_ru', '').strip()
        title_en = self.cleaned_data.get('title_en', '').strip()

        # Birinchi to'ldirilgan titleni olish
        instance.title = title_uz or title_ru or title_en or ''

        if commit:
            instance.save()
        return instance

from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name_uz', 'name_ru', 'name_en', 'description_uz', 'description_ru', 'description_en', 'slug',
                  'image', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Barcha name maydonlarini majburiy qilish
        self.fields['name_uz'].required = True
        self.fields['name_ru'].required = True
        self.fields['name_en'].required = True

        # Slug maydonini sozlash
        self.fields['slug'].required = False
        self.fields['slug'].widget.attrs.update({
            'class': 'form-control bg-light',
            'readonly': True,
            'placeholder': 'Avtomatik yaratiladi'
        })

        # Maydon label va placeholderlarini sozlash
        field_config = {
            'name_uz': {'label': _("Nomi (Oʻzbekcha)"), 'placeholder': _("Kategoriya nomi")},
            'name_ru': {'label': _("Название (Русский)"), 'placeholder': _("Название категории")},
            'name_en': {'label': _("Name (English)"), 'placeholder': _("Category name")},
            'description_uz': {'label': _("Tavsif (Oʻzbekcha)"), 'placeholder': _("Kategoriya tavsifi")},
            'description_ru': {'label': _("Описание (Русский)"), 'placeholder': _("Описание категории")},
            'description_en': {'label': _("Description (English)"), 'placeholder': _("Category description")},
        }

        for field_name, config in field_config.items():
            if field_name in self.fields:
                self.fields[field_name].label = config['label']
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': config['placeholder'],
                    'required': field_name.startswith('name_')  # Faqat name maydonlari uchun required
                })

        # name_uz maydoni o'zgarganda slug ni yangilash
        if 'name_uz' in self.fields:
            self.fields['name_uz'].widget.attrs.update({
                'oninput': 'generateSlugFromUzName()'
            })

    def clean(self):
        cleaned_data = super().clean()

        # Barcha name maydonlari to'ldirilganligini tekshirish
        for lang in ['uz', 'ru', 'en']:
            if not cleaned_data.get(f'name_{lang}'):
                self.add_error(f'name_{lang}', _("Ushbu maydon majburiy"))

        # Slug ni avtomatik yaratish
        if not cleaned_data.get('slug') and cleaned_data.get('name_uz'):
            base_slug = slugify(cleaned_data['name_uz'])
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.instance.pk if self.instance else None).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            cleaned_data['slug'] = slug

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Generate slug from name_uz if slug is empty
        if not instance.slug and instance.name_uz:
            base_slug = slugify(instance.name_uz)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug

        if commit:
            instance.save()

        return instance


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name_uz', 'name_ru', 'name_en', 'description_uz', 'description_ru', 'description_en',
                  'logo', 'slug', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Slug maydonini sozlash
        self.fields['slug'].required = False
        self.fields['slug'].widget.attrs.update({
            'class': 'form-control',
            'readonly': True
        })

        # Logo majburiy qilish
        self.fields['logo'].required = True

        # Maydonlar uchun sozlashlar
        fields_config = {
            'name_uz': {'label': _("Nomi (Oʻzbekcha)"), 'placeholder': _("Brend nomi")},
            'name_ru': {'label': _("Название (Русский)"), 'placeholder': _("Название бренда")},
            'name_en': {'label': _("Name (English)"), 'placeholder': _("Brand name")},
            'description_uz': {'label': _("Tavsif (Oʻzbekcha)"), 'placeholder': _("Brend tavsifi")},
            'description_ru': {'label': _("Описание (Русский)"), 'placeholder': _("Описание бренда")},
            'description_en': {'label': _("Description (English)"), 'placeholder': _("Brand description")},
        }

        for field_name, config in fields_config.items():
            if field_name in self.fields:
                self.fields[field_name].label = config['label']
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': config['placeholder'],
                    'required': field_name.startswith('name_')  # Faqat name maydonlari uchun required
                })

        # Textarea uchun qo'shimcha sozlashlar
        for field in ['description_uz', 'description_ru', 'description_en']:
            if field in self.fields:
                self.fields[field].widget.attrs.update({
                    'rows': 3
                })

    def clean(self):
        cleaned_data = super().clean()

        # Barcha name maydonlari to'ldirilganligini tekshirish
        for lang in ['uz', 'ru', 'en']:
            if not cleaned_data.get(f'name_{lang}'):
                self.add_error(f'name_{lang}', _("Ushbu maydon majburiy"))

        # Slug ni avtomatik yaratish
        if not cleaned_data.get('slug') and cleaned_data.get('name_uz'):
            base_slug = slugify(cleaned_data['name_uz'])
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(pk=self.instance.pk if self.instance else None).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            cleaned_data['slug'] = slug

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Generate slug from name_uz if slug is empty
        if not instance.slug and instance.name_uz:
            base_slug = slugify(instance.name_uz)
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug

        if commit:
            instance.save()

        return instance


class CarModelForm(forms.ModelForm):
    class Meta:
        model = CarModel
        fields = [
            'brand', 'image',
            'name_uz', 'name_ru', 'name_en',
            'slug',
            'description_uz', 'description_ru', 'description_en',
            'is_active'
        ]
        widgets = {
            'description_uz': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'description_ru': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'description_en': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control select2'}),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'data-avto-yaratilgan': 'true'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Majburiy maydonlar
        self.fields['brand'].required = True
        self.fields['image'].required = not bool(self.instance.pk)  # Faqat yangi yaratishda majburiy
        self.fields['name_uz'].required = True
        self.fields['name_ru'].required = False  # Ruscha nom majburiy emas
        self.fields['name_en'].required = False  # Inglizcha nom majburiy emas

        # Slug maydoni sozlamalari
        self.fields['slug'].required = False
        self.fields['slug'].widget.attrs.update({
            'placeholder': _("Avtomatik yaratiladi"),
            'help_text': _("URL uchun ishlatiladigan qisqa nom"),
            'readonly': True
        })

        # Maydonlar uchun sarlavhalar
        self.fields['brand'].label = _("Brend")
        self.fields['image'].label = _("Model rasmi")
        self.fields['is_active'].label = _("Faol")
        self.fields['is_active'].initial = True  # Yangi modellar uchun aktiv holatda

        # Tillar bo'yicha sozlamalar
        name_config = {
            'name_uz': {'label': _("Oʻzbekcha nom"), 'placeholder': _("Model nomi")},
            'name_ru': {'label': _("Ruscha nom"), 'placeholder': _("Название модели")},
            'name_en': {'label': _("Inglizcha nom"), 'placeholder': _("Model name")},
        }

        description_config = {
            'description_uz': {'label': _("Oʻzbekcha tavsif"), 'placeholder': _("Model haqida ma'lumot")},
            'description_ru': {'label': _("Ruscha tavsif"), 'placeholder': _("Описание модели")},
            'description_en': {'label': _("Inglizcha tavsif"), 'placeholder': _("Model description")},
        }

        for field_name, config in name_config.items():
            self.fields[field_name].label = config['label']
            self.fields[field_name].widget.attrs['placeholder'] = config['placeholder']

        for field_name, config in description_config.items():
            self.fields[field_name].label = config['label']
            self.fields[field_name].widget.attrs['placeholder'] = config['placeholder']

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get('brand')
        slug = cleaned_data.get('slug')
        name_uz = cleaned_data.get('name_uz')

        # Kamida bitta nom kiritilganligini tekshirish
        if not any(cleaned_data.get(f'name_{lang}') for lang in ['uz', 'ru', 'en']):
            raise forms.ValidationError(_("Kamida bitta til uchun nom kiritishingiz kerak"))

        # Agar slug kiritilmagan bo'lsa, o'zbekcha nomdan avtomatik yaratish
        if not slug and name_uz:
            cleaned_data['slug'] = self.generate_unique_slug(name_uz, brand)

        # Slug va brend kombinatsiyasining takrorlanmasligini tekshirish
        if brand and 'slug' in cleaned_data:
            self.validate_unique_slug(brand, cleaned_data['slug'])

        return cleaned_data

    def generate_unique_slug(self, name, brand):
        """Takrorlanmas slug yaratish"""
        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        while True:
            qs = CarModel.objects.filter(brand=brand, slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if not qs.exists():
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    def validate_unique_slug(self, brand, slug):
        """Slugning takrorlanmasligini tekshirish"""
        qs = CarModel.objects.filter(brand=brand, slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError({
                'slug': _("Ushbu brend uchun bunday slug bilan model allaqachon mavjud")
            })

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Agar slug bo'sh bo'lsa, o'zbekcha nomdan yaratish
        if not instance.slug and self.cleaned_data.get('name_uz'):
            instance.slug = self.generate_unique_slug(
                self.cleaned_data['name_uz'],
                self.cleaned_data['brand']
            )

        if commit:
            instance.save()
            self.save_m2m()  # Agar many-to-many maydonlari bo'lsa

        return instance


class OrderForm(forms.ModelForm):
    status = forms.ChoiceField(choices=Order.STATUS_CHOICES, label="Holat")
    payment_confirmed = forms.BooleanField(
        required=False,
        label="To'lov tasdiqlangan"
    )
    estimated_delivery_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Yetkazib berish sanasi"
    )

    class Meta:
        model = Order
        fields = ['status', 'payment_confirmed', 'estimated_delivery_date']



class ExchangeRateForm(forms.Form):
    usd_to_uzs = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        label="1 USD = UZS"
    )
    class Meta:
        model =ExchangeRate
        fields = ['usd_to_uzs',]

class PaymentSettingsForm(forms.Form):
    card_number = forms.CharField(max_length=20, label="Karta raqami")
    card_holder_name = forms.CharField(max_length=100, label="Karta egasi")
    bank_name = forms.CharField(max_length=100, label="Bank nomi")

    class Meta:
        model = PaymentSettings
        fields = ['card_number', 'card_holder_name', 'bank_name']

