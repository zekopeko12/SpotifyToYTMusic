from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from ytmusicapi import YTMusic, OAuthCredentials
from dotenv import load_dotenv
import time, os

load_dotenv()

yt_client_id = os.getenv("YT_MUSIC_CLIENT_ID")
yt_client_secret = os.getenv("YT_MUSIC_CLIENT_SECRET")

spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

ytmusic = YTMusic('oauth.json', oauth_credentials=OAuthCredentials(client_id=yt_client_id, client_secret=yt_client_secret))
auth_manager = SpotifyClientCredentials()
spotify = Spotify(auth_manager=auth_manager)

spotify_user_id = "5gkug6mlufw8644llwq85c0ul"
playlists = spotify.user_playlists(spotify_user_id)

def get_all_spotify_tracks(sp, playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id)
    tracks.extend(results['items'])
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

BATCH_SIZE = 50

for playlist in playlists['items']:
    playlist_name = playlist['name']
    print(f"\nProcessing playlist: {playlist_name}")

    existing_playlists = ytmusic.get_library_playlists()
    ytm_playlist = next((p for p in existing_playlists if p['title'] == playlist_name), None)

    if not ytm_playlist:
        ytm_playlist_id = ytmusic.create_playlist(
            playlist_name, 
            f"Imported from Spotify playlist {playlist_name}"
        )

        print(f"Created YTMusic playlist: {playlist_name}")
    else:
        ytm_playlist_id = ytm_playlist['playlistId']
        print(f"Found existing YTMusic playlist: {playlist_name}")

    tracks = get_all_spotify_tracks(spotify, playlist['id'])
    print(f"Total tracks to transfer: {len(tracks)}")
    
    ids_to_add = []
    for item in tracks:
        track = item['track']
        track_name = track['name']
        track_artist = track['artists'][0]['name']

        search_results = ytmusic.search(f"{track_name} {track_artist}", filter="songs")

        if not search_results:
            print(f"Not found on YTMusic: {track_name} - {track_artist}")
            continue

        song_results = [item for item in search_results if item.get("resultType") == "song"]

        exclude_keywords = ["live", "remix", "cover", "edit", "acoustic"]
        filtered_results = [
            s for s in song_results
            if not any(kw.lower() in s['title'].lower() for kw in exclude_keywords)
        ]

        if filtered_results:
            selected = filtered_results[0]
        elif song_results:
            selected = song_results[0]
        else:
            print(f"Not found on YTMusic: {track_name} - {track_artist}")
            continue

        ids_to_add.append(selected['videoId'])

        if len(ids_to_add) == BATCH_SIZE:
            ytmusic.add_playlist_items(ytm_playlist_id, ids_to_add)
            ids_to_add = []

        time.sleep(0.5)

    if ids_to_add:
        ytmusic.add_playlist_items(ytm_playlist_id, ids_to_add)

    print(f"Finished transfering playlist: {playlist_name}")