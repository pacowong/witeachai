from pytube import YouTube

url = "https://www.youtube.com/watch?v=HeQwAggzkNc"
YouTube(url).streams.first().download()