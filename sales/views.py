from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny)
#IsAuthenticatedOrReadOnly
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from django.db.models import Sum, F

from .models import Customer, Product, Order, OrderItem
from .serializers import (
    CustomerSerializer,
    ProductSerializer,
    OrderSerializer,
    OrderStatusSerializer
)

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        company = self.request.query_params.get('company')
        if company:
            queryset = queryset.filter(company_name__icontains=company)
        return queryset

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(is_active=True)
        name = self.request.query_params.get('name')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        return queryset

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        status = self.request.query_params.get('status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if status:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        return queryset

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SalesReportView(generics.GenericAPIView):
    def get(self, request):
        start_date_str = request.query_params.get('start')
        end_date_str = request.query_params.get('end')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

            if start_date and end_date and end_date < start_date:
                return Response(
                    {"error": "End date cannot be earlier than start date"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except ValueError as e:
            return Response(
                {"error": f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            orders = Order.objects.all()
            if start_date:
                orders = orders.filter(created_at__date__gte=start_date)
            if end_date:
                orders = orders.filter(created_at__date__lte=end_date)

            confirmed_orders = orders.filter(status='confirmed')

            if not confirmed_orders.exists():
                return Response(
                    {
                        "error": "No confirmed orders found for the selected period",
                        "start_date": start_date_str,
                        "end_date": end_date_str
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # Расчет показателей с правильным преобразованием типов
            total_revenue = sum(float(Decimal(str(order.total_amount))) for order in confirmed_orders)
            order_count = confirmed_orders.count()

            # Топ-5 клиентов по выручке (с учетом total_spent)
            customer_totals = defaultdict(float)
            for order in confirmed_orders:
                try:
                    order_total = float(Decimal(str(order.total_amount)))
                    customer_totals[order.customer] += order_total
                except (TypeError, ValueError) as e:
                    continue  # Пропускаем заказы с некорректными суммами

            # Изменение: передаем и клиента, и total_spent в качестве словаря
            top_customers_with_total = sorted(
                [(customer, total) for customer, total in customer_totals.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]

            # Самый популярный товар
            popular_product = (
                Product.objects
                .filter(orderitem__order__in=confirmed_orders)
                .annotate(total_quantity=Sum('orderitem__quantity'))
                .order_by('-total_quantity')
                .first()
            )

            # Подготовка контекста
            context = {
                'start_date': start_date_str or '—',
                'end_date': end_date_str or '—',
                'total_revenue': Decimal(str(total_revenue)),
                'order_count': order_count,
                # Изменение: передаем список словарей для top_customers
                'top_customers': [
                    {'customer': customer, 'total_spent': total}
                    for customer, total in top_customers_with_total
                ],
                'popular_product': popular_product,
                'orders': confirmed_orders.order_by('-created_at'),
                'now': datetime.now(),
            }

            # Генерация PDF
            try:
                template = get_template('sales_report.html')
                html_string = template.render(context)

                pdf = HTML(
                    string=html_string,
                    base_url=request.build_absolute_uri('/')
                ).write_pdf()

                response = HttpResponse(pdf, content_type='application/pdf')
                filename = f"sales_report_{start_date_str or 'all'}_{end_date_str or 'all'}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

            except Exception as render_error:
                return Response(
                    {
                        "error": "PDF generation failed",
                        "detail": str(render_error),
                        "solution": "Check template syntax and WeasyPrint installation"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as db_error:
            return Response(
                {
                    "error": "Database error occurred",
                    "detail": str(db_error),
                    "solution": "Check database connection and query parameters"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
