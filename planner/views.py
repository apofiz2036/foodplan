from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
import random
from datetime import timedelta

from .forms import LoginForm, RegisterForm, UserProfileForm
from .models import UserProfile, DietType, Dish, Allergy


User = get_user_model()


def index(request):
    return render(request, 'index.html')


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

    context = {
        'dish': dish,
        'ingredients': ingredients,
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

    # Проверка подписки
    if not profile.subscription_end_date or profile.subscription_end_date < timezone.now().date():
        messages.warning(request, "Ваша подписка истекла или не оформлена!")
        return redirect('order')

    if not profile.diet_type:
        messages.warning(request, "Выберите тип диеты в настройках профиля")
        return redirect('update_profile')

    form = UserProfileForm(instance=profile, user=user)

    # Получаем выбранные категории
    categories = []
    if profile.breakfast:
        categories.append('breakfast')
    if profile.lunch:
        categories.append('lunch')
    if profile.dinner:
        categories.append('dinner')
    if profile.dessert:
        categories.append('dessert')

    dishes_by_category = {}

    if categories:
        # Получаем все подходящие блюда
        dishes = Dish.objects.filter(
            diet_type=profile.diet_type,
            category__in=categories
        ).distinct()

        # Исключаем блюда с аллергенами пользователя
        if profile.allergies.exists():
            dishes = dishes.exclude(
                ingredients__allergens__in=profile.allergies.all()
            ).distinct()

        # Группируем блюда по категориям
        for category in categories:
            category_dishes = dishes.filter(category=category)
            dishes_by_category[f"{category}_dishes"] = category_dishes

    context = {
        'form': form,
        'profile': profile,
        'user': user,
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

    form = UserProfileForm(request.POST, instance=profile, user=user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Профиль обновлён!')
    else:
        messages.error(request, 'Ошибка при обновлении профиля.')

    return redirect('lk')

# Это точно нужно еще пересмотреть
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
