from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from ckeditor.fields import RichTextField
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate slug from name_uz if slug is empty
        if not self.slug and self.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(self.name_uz)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


    @property
    def product_count(self):
        return self.product.count()


# class SubCategory(models.Model):
#     category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
#     name = models.CharField(max_length=100)
#     slug = models.SlugField(unique=True)
#     description = models.TextField(blank=True)
#     image = models.ImageField(upload_to='subcategories/', blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         verbose_name_plural = 'Sub Categories'
#         ordering = ['name']
#
#     def __str__(self):
#         return f"{self.category.name} - {self.name}"


class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate slug from name_uz if slug is empty
        if not self.slug and self.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(self.name_uz)
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class CarModel(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    # year_from = models.IntegerField(blank=True, null=True)
    # year_to = models.IntegerField(blank=True, null=True)
    # engine_types = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='models/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['brand', 'slug']
        ordering = ['brand', 'name']

    def __str__(self):
        return f"{self.brand.name} {self.name}"

    def save(self, *args, **kwargs):
        # Generate slug from name_uz if slug is empty
        if not self.slug and self.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(self.name_uz)
            slug = base_slug
            counter = 1
            while CarModel.objects.filter(brand=self.brand, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


from django.db import models
from modeltranslation.translator import translator, TranslationOptions
from django.core.validators import MinValueValidator
from ckeditor.fields import RichTextField
from django.urls import reverse


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='product')
    # subcategory = models.ForeignKey('SubCategory', on_delete=models.CASCADE, blank=True, null=True)
    compatible_models = models.ManyToManyField('CarModel', related_name='products')
    description = RichTextField()
    short_description = models.TextField(max_length=500, blank=True)

    # Pricing (stored in USD)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    # Images
    main_image = models.ImageField(upload_to='products/')

    # Video
    youtube_video_id = models.CharField(max_length=50, blank=True, help_text="YouTube video ID (masalan: jL14SRWKA6c)")

    # Stock
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=500, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['description']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        # Generate slug from name_uz if slug is empty
        if not self.slug and self.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(self.name_uz)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def price_uzs(self):
        """Convert USD price to UZS"""
        try:
            exchange_rate = ExchangeRate.objects.get(is_active=True)
            return self.price_usd * exchange_rate.usd_to_uzs
        except ExchangeRate.DoesNotExist:
            return self.price_usd * 12000  # Default rate

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.filter(is_approved=True).count()

    @property
    def in_carts_count(self):
        """Number of distinct authenticated users who have this product in their cart"""
        return (CartItem.objects
                .filter(product=self, cart__user__isnull=False)
                .values('cart__user')
                .distinct()
                .count())


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"{self.product.name} - Image"


class ExchangeRate(models.Model):
    usd_to_uzs = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"1 USD = {self.usd_to_uzs} UZS"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate other exchange rates
            ExchangeRate.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class Banner(models.Model):
    title = models.CharField(max_length=200,  blank=True)
    image = models.ImageField(upload_to='banners/')
    link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, unique=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"


class TelegramAuth(models.Model):
    session_token = models.CharField(max_length=12, unique=True, null=True)  # QO'SHILDI!
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    code = models.CharField(max_length=6, blank=True, null=True)
    chat_id = models.TextField(default='default_id')
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.code}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class ProductLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username} likes {self.product.name}"


class ProductComment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    comment = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class PaymentSettings(models.Model):
    card_number = models.CharField(max_length=20)
    card_holder_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    admin_chat_id = models.CharField(max_length=50, blank=True, null=True, help_text="Telegram admin chat ID for notifications")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.card_number} - {self.bank_name}"


class AdminProfile(models.Model):
    """Extended profile for admin users with specific permissions"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    full_name = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Permission flags for restricted admins
    can_access_settings = models.BooleanField(default=False, help_text="Can access settings section")
    can_access_users = models.BooleanField(default=False, help_text="Can access users management")
    can_access_admins = models.BooleanField(default=False, help_text="Can access admin management")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Admin: {self.user.username} ({self.full_name or 'No full name'})"

    @property
    def is_super_admin(self):
        """Check if this admin has full access (can access settings, users, and admins)"""
        return self.can_access_settings and self.can_access_users and self.can_access_admins


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount_uzs = models.DecimalField(max_digits=15, decimal_places=2)
    exchange_rate_used = models.DecimalField(max_digits=10, decimal_places=2)

    # Customer info
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_address = models.TextField()

    # Payment
    payment_screenshot = models.ImageField(upload_to='payments/', blank=True)
    payment_confirmed = models.BooleanField(default=False)
    payment_confirmed_at = models.DateTimeField(blank=True, null=True)

    # Delivery
    estimated_delivery_date = models.DateField(blank=True, null=True)
    delivery_address = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    price_uzs = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price_usd(self):
        if self.price_usd is not None and self.quantity is not None:
            return self.price_usd * self.quantity
        return 0  # yoki None

    @property
    def total_price_uzs(self):
        if self.price_uzs is not None and self.quantity is not None:
            return self.price_uzs * self.quantity
        return 0  # yoki None


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f"Cart - {self.user.username}"
        return f"Cart - Session {self.session_key}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price_usd(self):
        return sum(item.total_price_usd for item in self.items.all())

    @property
    def total_price_uzs(self):
        return sum(item.total_price_uzs for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price_usd(self):
        return self.product.price_usd * self.quantity

    @property
    def total_price_uzs(self):
        return self.product.price_uzs * self.quantity