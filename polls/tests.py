import datetime

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
# from django.contrib.staticfiles.testing import StaticLiveServerTestCase
# from selenium.webdriver.firefox.webdriver import WebDriver

from .models import Question, Choice


def create_question(question_text, days):
    """
    Create a question with the given `question_text` and published the
    given number of `days` offset to now (negative for questions published
    in the past, positive for questions that have yet to be published).
    """
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


def create_choice(question, choice_text, votes=0):
    """
    Create a choice with the given `question` object, `choice_text`, and
    number of `votes` to initialize with .
    """
    return Choice.objects.create(question=question, choice_text=choice_text,
                                 votes=votes)


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is in the future
        """
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is older than 1 day.
        """
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """
        was_published_recently() returns True for questions whose pub_date
        is within the last day.
        """
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


class QuestionIndexViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='user', password='hunter2')
        self.user.is_superuser = True
        self.user.save()

    def test_no_questions(self):
        """
        If no questions exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse('polls:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_past_question(self):
        """
        Questions with a pub_date in the past are displayed on the
        index page.
        """
        q = create_question(question_text="Past question.", days=-30)
        create_choice(question=q, choice_text="A choice")
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            ['<Question: Past question.>']
        )

    def test_future_question(self):
        """
        Questions with a pub_date in the future aren't displayed on
        the index page.
        """
        q = create_question(question_text="Future question.", days=30)
        create_choice(question=q, choice_text="A choice")
        response = self.client.get(reverse('polls:index'))
        self.assertContains(response, "No polls are available.")
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_future_question_and_past_question(self):
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        q = create_question(question_text="Past question.", days=-30)
        create_choice(question=q, choice_text="A choice")
        q2 = create_question(question_text="Future question.", days=30)
        create_choice(question=q2, choice_text="Another choice")
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            ['<Question: Past question.>']
        )

    def test_two_past_questions(self):
        """
        The questions index page may display multiple questions.
        """
        q = create_question(question_text="Past question 1.", days=-30)
        create_choice(question=q, choice_text="A choice")
        q2 = create_question(question_text="Past question 2.", days=-5)
        create_choice(question=q2, choice_text="Another choice")
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            ['<Question: Past question 2.>', '<Question: Past question 1.>']
        )

    def test_question_with_choices(self):
        """
        The questions index page will display questions with choices.
        """
        q = create_question(question_text="Question with choices.", days=-5)
        create_choice(question=q, choice_text="Choice 1")
        create_choice(question=q, choice_text="Choice 2")
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            ['<Question: Question with choices.>']
        )

    def test_question_without_choices(self):
        """
        The questions index page will not display questions without choices.
        """
        create_question(question_text="Question without choices", days=-5)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_question_with_and_without_choices(self):
        """
        The questions index page will filter questions without choices
        and only display questions with choices.
        """
        q = create_question(question_text="Question with choices.", days=-5)
        create_choice(question=q, choice_text="Choice 1")
        create_choice(question=q, choice_text="Choice 2")
        create_question(question_text="Question without choices", days=-5)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            ['<Question: Question with choices.>']
        )

    def test_question_without_choices_authenticated(self):
        """
        The questions index page will display questions without choices
        because user is authenticated as superuser.
        """
        self.client.force_login(self.user)
        create_question(question_text="Question without choices", days=-5)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            ['<Question: Question without choices>']
        )

    def test_question_without_choices_unauthenticated(self):
        """
        The questions index page will not display questions without choices
        because user is unauthenticated as superuser.
        """
        create_question(question_text="Question without choices", days=-5)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(response.context['latest_question_list'], [])


class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(
            question_text='Future question.', days=5)
        create_choice(question=future_question, choice_text="A choice")
        url = reverse('polls:detail', args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(
            question_text='Past Question.', days=-5)
        create_choice(question=past_question, choice_text="A choice")
        url = reverse('polls:detail', args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)


class QuestionResultViewTests(TestCase):
    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(
            question_text='Future question.', days=5)
        create_choice(question=future_question, choice_text="A choice")
        url = reverse('polls:results', args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(
            question_text='Past Question.', days=-5)
        create_choice(question=past_question, choice_text="A choice")
        url = reverse('polls:results', args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)


"""
Here's some selenium code to try out sometime!
"""

# class MySeleniumTests(StaticLiveServerTestCase):
#     fixtures = ['user-data.json']

#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#         cls.selenium = WebDriver()
#         cls.selenium.implicitly_wait(10)

#     @classmethod
#     def tearDownClass(cls):
#         cls.selenium.quit()
#         super().tearDownClass()

#     def test_login(self):
#         self.selenium.get('%s%s' % (self.live_server_url, '/login/'))
#         username_input = self.selenium.find_element_by_name("username")
#         username_input.send_keys('myuser')
#         password_input = self.selenium.find_element_by_name("password")
#         password_input.send_keys('secret')
#         self.selenium.find_element_by_xpath('//input[@value="Log in"]').click()
