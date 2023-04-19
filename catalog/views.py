import datetime
import uuid

from django.shortcuts import render, get_object_or_404
from .models import Book, Author, BookInstance, Genre
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy

from catalog.forms import RenewBookForm, Pages

# Create your views here.
def index(request):

    # generate counts of some of the main object
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()

    # available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()

    num_authors = Author.objects.count()

    num_books_series = BookInstance.objects.filter(book__title__icontains='chupacu').count()

    num_books_genre = BookInstance.objects.filter(book__genre__name__icontains='adult').count()

    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_books_series': num_books_series,
        'num_books_genre': num_books_genre,
        'num_visits': num_visits
    }

    # render the HTML template index.html
    return render(request, 'index.html', context=context)

class BookListView(generic.ListView):
    model = Book
    context_object_name = 'book_list'
    paginate_by = 10
    # queryset = Book.objects.filter(title__icontains='war')[:5]
    # template_name = 'books/allbooks.html'

    # def get_queryset(self):
    #     return Book.objects.filter(title__icontains='war')[:5] # Get 5 books containing the title war
    #
    # def get_context_data(self, **kwargs):
    #     # Call the base implementation first to get the context
    #     context = super(BookListView, self).get_context_data(**kwargs)
    #     # Create any data and add it to the context
    #     context['some_data'] = 'This is just some data'
    #     return context

class BookDetailView(generic.DetailView):
    model = Book

# class AuthorLisView(generic.ListView):

def authors_list_view(request):
    authors_list = Author.objects.all()
    pagination = 50
    start = 0
    end = len(authors_list)
    pages = 1
    if request.method == 'GET':
        form = Pages(initial={'page': 1})
    if len(authors_list) > pagination:
        r = len(authors_list) % pagination
        if r == 0:
            pages = int(len(authors_list) / pagination)
        else:
            pages = int(len(authors_list) / pagination) + 1
        end = pagination
        if request.method == "POST":
            form = Pages(request.POST)
            p = int(request.POST['page']) # form.cleaned_data['page'] did not work here idk y
            if p > pages:
                p = pages
            end = p * pagination
            start = end - pagination

    authors_list = authors_list[start:end]

    context = {
        'authors_list': authors_list,
        'pagination': pagination,
        'form': form,
        'pages': pages,
    }
    return render(request, 'author_list.html', context=context)

def author_detail_view(request, pk):
    try:
        author = Author.objects.get(pk=pk)
    except Author.DoesNotExist:
        raise Http404('Author does not exist')

    return render(request, 'author_detail.html', context={'author': author})

class LoanedBooksByUserListView(LoginRequiredMixin,generic.ListView):
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return (
            BookInstance.objects.filter(borrower=self.request.user)
            .filter(status__exact='o')
            .order_by('due_back')
        )

# @permission_required
# def LoanedBooksForLibrariansList():
#     model = BookInstance
#     template_name = 'catalog/bookinstance_librarian_view_list_borrowed.html'
#     paginate_by = 10
#     permission_required = 'catalog.can_mark_returned'
#
#     def get_queryset(self):
#         return (
#             BookInstance.objects.filter(status__exact='o').order_by('due_back')
#         )

class LoanedBooksForLibrariansList(PermissionRequiredMixin, generic.ListView):
    model = BookInstance
    template_name = 'catalog/bookinstance_librarian_view_list_borrowed.html'
    paginate_by = 10
    permission_required = 'catalog.can_mark_returned'

    def get_queryset(self):
        return (
            BookInstance.objects.filter(status__exact='o').order_by('due_back')
        )

# class LoanedBooksForLibrariansListPermission(PermissionRequiredMixin, LoanedBooksForLibrariansList):
#     permission_required = 'catalog.can_mark_returned'

@login_required
@permission_required('catalog.can_mark_returned', raise_exception=True)
def renew_book_librarian(request, pk):
    book_instance = get_object_or_404(BookInstance, pk=pk)

    # check if this is a post request, i.e. not the first time it is called
    if request.method == 'POST':
        # create a form instance and populate with data from the request (binding)
        form = RenewBookForm(request.POST)
        # check if form is valid
        if form.is_valid():
            # process the data in form.cleaned_data as required
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()

            # redirect to a new URL:
            return HttpResponseRedirect(reverse('all-borrowed'))
    # if this is a GET or any other method, create the default form
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookForm(initial={'renewal_date': proposed_renewal_date})

    context = {
        'form': form,
        'book_instance': book_instance,
    }

    return render(request, 'catalog/book_renew_librarian.html', context)

class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    initial = {'date_of_death': '04/18/2023'}
    permission_required = 'catalog.can_mark_returned'

class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    fields = '__all__' # not recommended, though.
    permission_required = 'catalog.can_mark_returned'

class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.can_mark_returned'

class BookCreate(PermissionRequiredMixin, CreateView):
    model = Book
    fields = [
        'title',
        'author',
        'summary',
        'isbn',
        'genre',
        'language',
    ]
    permission_required = 'catalog.can_mark_returned'

class BookUpdate(PermissionRequiredMixin, UpdateView):
    model = Book
    fields = [
        'title',
        'author',
        'summary',
        'isbn',
        'genre',
        'language',
    ]
    permission_required = 'catalog.can_mark_returned'

class BookDelete(PermissionRequiredMixin, DeleteView):
    model = Book
    success_url = reverse_lazy('books')
    permission_required = 'catalog.can_mark_returned'

class BookInstanceCreate(PermissionRequiredMixin, CreateView):
    model = BookInstance
    permission_required = 'catalog.can_mark_returned'
    fields = [
        'id',
        'book',
        'imprint',
    ]
    initial = {'id': uuid.uuid4}

class BookInstanceUpdate(PermissionRequiredMixin, UpdateView):
    model = BookInstance
    permission_required = 'catalog.can_mark_returned'
    fields = [
        'book',
        'imprint',
        'status',
        'due_back',
        'borrower',
    ]

class BookInstanceDelete(PermissionRequiredMixin, DeleteView):
    model = BookInstance
    success_url = reverse_lazy('books')
    permission_required = 'catalog.can_mark_returned'
