from django.core.paginator import Paginator, EmptyPage


def paginate_queryset(queryset, page_num, page_size):
    # 统一在这里保证 page_num 和 page_size 合法
    page_num = max(1, int(page_num))
    page_size = max(1, int(page_size))

    paginator = Paginator(queryset, page_size)

    if page_num > paginator.num_pages:
        page_num = paginator.num_pages

    try:
        page = paginator.page(page_num)
        return page, paginator.count
    except EmptyPage:
        raise ValueError('分页超出范围！')
