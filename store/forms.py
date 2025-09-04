from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'delivery_type', 'notes']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number',
                'required': True
            }),
            'delivery_type': forms.RadioSelect(attrs={
                'class': 'delivery-type-radio',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Order notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_type'].initial = 'office'
        self.fields['delivery_type'].widget.choices = Order.DELIVERY_TYPE_CHOICES
        
        # Add branch selection fields
        self.fields['region'] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'id': 'region-select',
                'required': True
            })
        )
        
        self.fields['branch'] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'id': 'branch-select',
                'required': True,
                'disabled': True
            })
        )
        
        # Add home delivery fields
        self.fields['home_address'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Address',
                'id': 'home-address',
                'style': 'display: none;'
            })
        )
        
        self.fields['city'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City',
                'id': 'city',
                'style': 'display: none;'
            })
        )
        
        self.fields['postal_code'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal Code',
                'id': 'postal-code',
                'style': 'display: none;'
            })
        )
    
    def clean(self):
        cleaned_data = super().clean()
        delivery_type = cleaned_data.get('delivery_type')
        
        if delivery_type == 'office':
            branch_id = self.data.get('branch')
            if not branch_id:
                self.add_error('branch', 'Please select a branch')
            else:
                # Store branch ID in cleaned_data
                cleaned_data['branch_id'] = branch_id
        else:  # home delivery
            if not cleaned_data.get('home_address'):
                self.add_error('home_address', 'This field is required')
            if not cleaned_data.get('city'):
                self.add_error('city', 'This field is required')
        
        return cleaned_data


