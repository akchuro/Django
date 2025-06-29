from rest_framework import serializers
from .models import Customer, Product, Order, OrderItem
from django.core.exceptions import ValidationError
from django.utils import timezone


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'full_name', 'email', 'company_name',
            'phone', 'created_at', 'discount_percent'
        ]
        read_only_fields = ['created_at']
        extra_kwargs = {
            'email': {'required': True},
            'phone': {'required': True}
        }

    def validate_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Скидка должна быть между 0 и 100%")
        return value


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price',
            'stock_quantity', 'is_active', 'discount_percent'
        ]
        extra_kwargs = {
            'price': {'min_value': 0},
            'stock_quantity': {'min_value': 0},
            'discount_percent': {'min_value': 0, 'max_value': 100}
        }

    def validate(self, data):
        if data.get('stock_quantity', 0) == 0 and data.get('is_active', True):
            raise serializers.ValidationError(
                "Товар с нулевым остатком не может быть активным"
            )
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        source='product',
        write_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_id', 'product_name', 'product_price',
            'quantity', 'price'
        ]
        read_only_fields = ['price']
        extra_kwargs = {
            'quantity': {'min_value': 1}
        }

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)

        if product.stock_quantity < quantity:
            raise serializers.ValidationError(
                f"Недостаточно товара на складе. Доступно: {product.stock_quantity}"
            )

        if not product.is_active:
            raise serializers.ValidationError("Этот товар недоступен для заказа")

        return data


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        source='customer',
        write_only=True
    )
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_discounts = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_tax = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_delivery = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 'customer_id', 'customer_name', 'status',
            'created_at', 'updated_at', 'delivery_cost',
            'tax_percent', 'items', 'subtotal', 'total_discounts',
            'total_tax', 'total_delivery', 'total_amount'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'subtotal',
            'total_discounts', 'total_tax', 'total_delivery',
            'total_amount'
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Заказ должен содержать хотя бы один товар")
        return value

    def validate_status(self, value):
        if self.instance and self.instance.status == 'cancelled' and value != 'cancelled':
            raise serializers.ValidationError("Отмененный заказ нельзя изменить")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                quantity=item_data['quantity'],
                price=item_data['product'].price
            )

        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # Обновляем основные поля заказа
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Если есть обновление позиций
        if items_data is not None:
            # Удаляем старые позиции
            instance.items.all().delete()
            # Создаем новые
            for item_data in items_data:
                OrderItem.objects.create(
                    order=instance,
                    product=item_data['product'],
                    quantity=item_data['quantity'],
                    price=item_data['product'].price
                )

        instance.save()
        return instance


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']

    def validate_status(self, value):
        valid_transitions = {
            'draft': ['confirmed', 'cancelled'],
            'confirmed': ['shipped', 'cancelled'],
            'shipped': [],
            'cancelled': []
        }

        current_status = self.instance.status
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Недопустимый переход статуса из {current_status} в {value}"
            )
        return value