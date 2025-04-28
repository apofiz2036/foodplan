from datetime import timedelta
import random

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm, UserProfileForm
from .models import Allergy, DietType, Dish, UserProfile


User = get_user_model()


def index(request):
    context = {
        'current_date': timezone.now().date()
    }
    return render(request, 'index.html', context)


def auth(request):
    if request.user.is_authenticated:
        return redirect('lk')
    return render(request, 'auth.html')


def registration(request):
    if request.user.is_authenticated:
        return redirect('lk')
    return render(request, 'registration.html')


def dish_card(request, dish_id):
    dish = get_object_or_404(Dish, id=dish_id)
    ingredients = dish.dishingredient_set.all()
    profile = request.user.userprofile

    # Умножаем количество каждого ингредиента на количество персон
    adjusted_ingredients = []
    for ingredient in ingredients:
        adjusted_quantity = float(ingredient.quantity) * profile.count_of_persons
        adjusted_ingredients.append({
            'ingredient': ingredient.ingredient,
            'quantity': adjusted_quantity,
            'unit': ingredient.ingredient.get_unit_display()
        })

    context = {
        'dish': dish,
        'ingredients': adjusted_ingredients,
        'profile': profile,
    }
    return render(request, 'card.html', context)


@login_required
def lk_view(request):
    user = request.user
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        messages.error(request, "Профиль пользователя не найден")
        return redirect('index')

    # Проверка активности подписки
    subscription_active = profile.subscription_end_date and profile.subscription_end_date >= timezone.now().date()
    dishes_by_category = {}

    if subscription_active and profile.diet_type:
        # Логика фильтрации блюд только если подписка активна и выбран тип диеты
        categories = []
        if profile.breakfast:
            categories.append('breakfast')
        if profile.lunch:
            categories.append('lunch')
        if profile.dinner:
            categories.append('dinner')
        if profile.dessert:
            categories.append('dessert')

        if categories:
            dishes = Dish.objects.filter(
                diet_type=profile.diet_type,
                category__in=categories
            ).distinct()

            if profile.allergies.exists():
                dishes = dishes.exclude(
                    ingredients__allergens__in=profile.allergies.all()
                ).distinct()

            # Рассчитываем стоимость с учетом количества персон
            adjusted_dishes = []
            for dish in dishes:
                dish.adjusted_price = dish.total_price * profile.count_of_persons
                dish.adjusted_calories = dish.total_calories * profile.count_of_persons
                adjusted_dishes.append(dish)

            if profile.budget_limit:
                adjusted_dishes = [dish for dish in adjusted_dishes
                                   if dish.adjusted_price <= profile.budget_limit]

            # Группируем блюда по категориям
            for category in categories:
                category_dishes = [d for d in adjusted_dishes if d.category == category]
                dishes_by_category[f"{category}_dishes"] = category_dishes

    form = UserProfileForm(instance=profile, user=user)

    context = {
        'form': form,
        'profile': profile,
        'user': user,
        'subscription_active': subscription_active,
        **dishes_by_category
    }

    return render(request, 'lk.html', context)


@login_required
def order(request):
    return render(request, 'order.html')


def card(request):
    return render(request, 'card.html')


def auth_view(request):
    if request.user.is_authenticated:
        return redirect('lk')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                next_url = request.POST.get('next', '')
                return redirect(next_url if next_url else 'lk')
            else:
                messages.error(request, 'Неверный логин или пароль')
    else:
        form = LoginForm()

    next_url = request.GET.get('next', '')
    return render(request, 'auth.html', {
        'form': form,
        'next': next_url
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('lk')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()

            UserProfile.objects.create(
                user=user,
                diet_type=form.cleaned_data.get('diet_type'),
                breakfast=True,
                lunch=True,
                dinner=True,
                dessert=False
            )

            login(request, user)
            return redirect('order')
    else:
        form = RegisterForm()

    return render(request, 'registration.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('index')


@login_required
def order_view(request):
    return render(request, 'order.html')


@require_POST
@login_required
def update_profile(request):
    user = request.user
    profile = user.userprofile

    form = UserProfileForm(request.POST, request.FILES, instance=profile, user=user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Профиль обновлён!')
    else:
        messages.error(request, 'Ошибка при обновлении профиля.')

    return redirect('lk')


@login_required
@require_POST
def update_avatar(request):
    profile = request.user.userprofile
    if 'avatar' in request.FILES:
        profile.avatar = request.FILES['avatar']
        profile.save()
        messages.success(request, 'Аватар успешно обновлен!')
    else:
        messages.error(request, 'Не удалось загрузить аватар')
    return redirect('lk')


@login_required
@require_POST
def process_order(request):
    user = request.user
    profile = user.userprofile

    # Обновляем параметры подписки
    profile.breakfast = request.POST.get('select1') == '0'
    profile.lunch = request.POST.get('select2') == '0'
    profile.dinner = request.POST.get('select3') == '0'
    profile.dessert = request.POST.get('select4') == '0'

    # Обновляем количество персон
    persons_mapping = {'0': 1, '1': 2, '2': 3, '3': 4, '4': 5, '5': 6}
    profile.count_of_persons = persons_mapping.get(request.POST.get('select5', '0'), 1)

    # Обновляем тип диеты
    diet_type_name = {
        'classic': 'Классическое',
        'low': 'Низкоуглеводное',
        'veg': 'Вегетарианское',
        'keto': 'Кето'
    }.get(request.POST.get('foodtype'))

    if diet_type_name:
        profile.diet_type = DietType.objects.get(name=diet_type_name)

    # Обновляем аллергии
    profile.allergies.clear()
    allergy_map = {
        'allergy1': 'Рыба и морепродукты',
        'allergy2': 'Мясо',
        'allergy3': 'Зерновые',
        'allergy4': 'Продукты пчеловодства',
        'allergy5': 'Орехи и бобовые',
        'allergy6': 'Молочные продукты'
    }

    for field, allergy_name in allergy_map.items():
        if field in request.POST:
            allergy, created = Allergy.objects.get_or_create(name=allergy_name)
            profile.allergies.add(allergy)

    # Устанавливаем дату окончания подписки в зависимости от выбранного срока
    duration_mapping = {
        '0': 30,  # 1 месяц
        '1': 90,  # 3 месяца
        '2': 180,  # 6 месяцев
        '3': 365  # 12 месяцев
    }
    duration_days = duration_mapping.get(request.POST.get('duration', '0'), 30)
    profile.subscription_end_date = timezone.now().date() + timedelta(days=duration_days)
    profile.save()

    messages.success(request, "Подписка оформлена успешно!")
    return redirect('lk')
