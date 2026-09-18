#!/usr/bin/env python3
"""Build a Kdenlive 23.04+ project referencing Snapshot's multistream MKV."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET

from process_env import system_program_env


def props(node, values):
    for key, value in values.items():
        ET.SubElement(node, 'property', name=key).text = str(value)
    return node


def effect(entry, service, name, values):
    return props(ET.SubElement(entry, 'filter'), {
        'mlt_service': service, 'kdenlive_id': service, 'kdenlive:effectName': name,
        'kdenlive:ix': len(entry.findall('filter')), 'kdenlive:sync_in_out': 1,
        **values})


def generate(media, output, fps, size, margin, position, mirror):
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(media)],
        env=system_program_env()))
    videos = [s for s in probe['streams'] if s['codec_type'] == 'video']
    audios = [s for s in probe['streams'] if s['codec_type'] == 'audio']
    if len(videos) != 2 or len(audios) not in (1, 2):
        raise ValueError('Expected screen, webcam, microphone, and optional system audio '
                         'streams (2 video + 1 or 2 audio).')
    duration = float(probe['format']['duration'])
    source_frames = max(1, math.ceil(duration * fps))
    # Round up to a common capture time at which every input is available.
    trim_start = max(0, math.ceil(max(float(s.get('start_time', 0))
                                    for s in videos + audios) * fps - 1e-9))
    if trim_start >= source_frames:
        raise ValueError('Recording has no interval with all inputs available.')
    frames = source_frames - trim_start
    width, height = videos[0]['width'], videos[0]['height']
    if size + 2 * margin > min(width, height):
        raise ValueError('Overlay and margin do not fit the screen.')
    uid = '{' + str(uuid.uuid4()) + '}'
    root = ET.Element('mlt', {'LC_NUMERIC': 'C', 'producer': 'main_bin', 'version': '7.22.0',
                              'root': str(output.parent)})
    ET.SubElement(root, 'profile', dict(description=f'Snapshot {width}x{height} {fps} fps', width=str(width), height=str(height),
        frame_rate_num=str(fps), frame_rate_den='1', progressive='1', sample_aspect_num='1',
        sample_aspect_den='1', display_aspect_num=str(width), display_aspect_den=str(height), colorspace='709'))
    black = ET.SubElement(root, 'producer', id='black', **{'in': '0', 'out': str(frames - 1)})
    props(black, {'resource': '0', 'mlt_service': 'color', 'length': frames, 'eof': 'pause'})
    # MLT's video producers count from the selected video's first timestamp;
    # its audio-only producer retains the container timeline. Convert the common
    # capture interval to those producer coordinates below.
    streams = [('mic', 'Microphone', audios[0], 4)]
    if len(audios) == 2:
        streams.append(('system_audio', 'System Audio', audios[1], 6))
    streams.extend((('screen', 'Screen', videos[0], 2),
                    ('webcam', 'Webcam', videos[1], 3)))
    for name, label, stream, bin_id in streams:
        chain = ET.SubElement(root, 'chain', id=name, out=str(source_frames - 1))
        audio = stream['codec_type'] == 'audio'
        props(chain, {'resource': media.name, 'mlt_service': 'avformat', 'length': source_frames,
            'eof': 'pause', 'seekable': 1, 'audio_index': stream['index'] if audio else -1,
            'video_index': -1 if audio else stream['index'],
            'vstream': -1 if audio else videos.index(stream),
            'astream': audios.index(stream) if audio else -1,
            'set.test_audio': 0 if audio else 1, 'set.test_image': 1 if audio else 0,
            'kdenlive:id': bin_id, 'kdenlive:clipname': label,
            'kdenlive:clip_type': 1 if audio else 2, 'kdenlive:folderid': -1})
    for name, label, stream, bin_id in streams:
        audio = stream['codec_type'] == 'audio'
        playlist = ET.SubElement(root, 'playlist', id=name + '_clips')
        if audio:
            props(playlist, {'kdenlive:audio_track': 1})
        video_offset = (0 if audio else math.floor(
            float(stream.get('start_time', 0)) * fps + 0.5))
        producer_in = max(0, trim_start - video_offset)
        entry = ET.SubElement(playlist, 'entry', producer=name,
                              **{'in': str(producer_in), 'out': str(producer_in + frames - 1)})
        props(entry, {'kdenlive:id': bin_id})
        if name == 'webcam':
            if mirror:
                effect(entry, 'avfilter.hflip', 'Flip Horizontally', {})
            vertical, horizontal = ('center', 'center') if position == 'center' else position.split('-')
            x = {'left': margin, 'center': (width-size)/2, 'right': width-size-margin}[horizontal]
            y = {'top': margin, 'center': (height-size)/2, 'bottom': height-size-margin}[vertical]
            # MLT fits source video to the profile before effects. Scale that
            # fitted image until its shorter side equals the circle diameter.
            fit = min(width / stream['width'], height / stream['height'])
            scale = size / (min(stream['width'], stream['height']) * fit)
            rw, rh = width * scale, height * scale
            # Mask in the fitted source coordinate system, then transform both
            # pixels and alpha together. Min preserves existing transparency;
            # writing a new opaque mask after Transform can expose black pixels.
            diameter = min(stream['width'], stream['height'])
            effect(entry, 'frei0r.alphaspot', 'Alpha shapes', {
                'Shape': 0.38, 'Position X': 0.5, 'Position Y': 0.5,
                'Size X': diameter/(2*stream['width']), 'Size Y': diameter/(2*stream['height']), 'Tilt': 0.5,
                'Transition width': 0.005, 'Min': 0, 'Max': 1, 'Operation': 0.5})
            effect(entry, 'qtblend', 'Transform', {
                'version': 2,
                'rect': f'0={x+(size-rw)/2:g} {y+(size-rh)/2:g} {rw:g} {rh:g} 1',
                'rotation': '0=0', 'compositing': 0, 'distort': 0, 'rotate_center': 1})
        empty = ET.SubElement(root, 'playlist', id=name + '_mix')
        if audio:
            props(empty, {'kdenlive:audio_track': 1})
        track = ET.SubElement(root, 'tractor', id=name + '_track', **{'in': '0', 'out': str(frames-1)})
        props(track, {'kdenlive:track_name': label, 'kdenlive:trackheight': 80,
                      'kdenlive:timeline_active': 1, **({'kdenlive:audio_track': 1} if audio else {})})
        for suffix in ('_clips', '_mix'):
            ET.SubElement(track, 'track', producer=name + suffix, hide='video' if audio else 'audio')
    groups = json.dumps([{
        'type': 'Normal',
        'children': [
            {'type': 'Leaf', 'leaf': 'clip', 'data': f'{track}:0:-1'}
            for track in range(len(streams))
        ],
    }], separators=(',', ':'))
    sequence = ET.SubElement(root, 'tractor', id='sequence', **{'in': '0', 'out': str(frames-1)})
    props(sequence, {'kdenlive:uuid': uid, 'kdenlive:id': 5, 'kdenlive:clipname': output.stem + ' (timeline)',
        'kdenlive:producer_type': 17, 'kdenlive:maxduration': frames,
        'kdenlive:sequenceproperties.documentuuid': uid, 'kdenlive:sequenceproperties.hasAudio': 1,
        'kdenlive:sequenceproperties.hasVideo': 1, 'kdenlive:sequenceproperties.tracksCount': len(streams),
        'kdenlive:sequenceproperties.activeTrack': len(streams) - 1, 'kdenlive:sequenceproperties.audioTarget': 0,
        'kdenlive:sequenceproperties.videoTarget': 1, 'kdenlive:sequenceproperties.position': 0,
        'kdenlive:sequenceproperties.zonein': 0, 'kdenlive:sequenceproperties.zoneout': frames,
        'kdenlive:sequenceproperties.groups': groups,
        'snapshot:trim_start_frames': trim_start})
    ET.SubElement(sequence, 'track', producer='black')
    for index, (name, _, stream, _) in enumerate(streams, 1):
        audio = stream['codec_type'] == 'audio'
        ET.SubElement(sequence, 'track', producer=name + '_track')
        props(ET.SubElement(sequence, 'transition'), {
            'a_track': 0, 'b_track': index, 'mlt_service': 'mix' if audio else 'qtblend',
            'internal_added': 237, 'always_active': 1,
            **({'sum': 1, 'accepts_blanks': 1} if audio else {'compositing': 0, 'distort': 0})})
    main_bin = ET.SubElement(root, 'playlist', id='main_bin')
    props(main_bin, {'xml_retain': 1, 'kdenlive:docproperties.version': '1.1',
        'kdenlive:docproperties.kdenliveversion': '23.08.5',
        'kdenlive:docproperties.documentid': int(time.time()*1000),
        'kdenlive:docproperties.uuid': uid, 'kdenlive:docproperties.activetimeline': uid,
        'kdenlive:docproperties.opensequences': uid, 'kdenlive:docproperties.audioChannels': 2,
        'kdenlive:docproperties.compositing': 1})
    for name in ('screen', 'webcam', 'mic') + (('system_audio',) if len(audios) == 2 else ()) + ('sequence',):
        ET.SubElement(main_bin, 'entry', producer=name,
                      **{'in': '0', 'out': str((frames if name == 'sequence' else source_frames)-1)})
    wrapper = ET.SubElement(root, 'tractor', id='project', **{'in': '0', 'out': str(frames-1)})
    props(wrapper, {'kdenlive:projectTractor': 1})
    ET.SubElement(wrapper, 'track', producer='sequence', **{'in': '0', 'out': str(frames-1)})
    ET.indent(root)
    with output.open('xb') as handle:
        ET.ElementTree(root).write(handle, encoding='utf-8', xml_declaration=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('media', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--fps', type=int, required=True)
    p.add_argument('--size', type=int, required=True)
    p.add_argument('--margin', type=int, required=True)
    p.add_argument('--position', required=True)
    p.add_argument('--no-mirror', action='store_true')
    args = p.parse_args()
    try:
        generate(args.media.resolve(), args.output.absolute(), args.fps, args.size,
                 args.margin, args.position, not args.no_mirror)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1, f'Kdenlive export failed: {exc}\n')


if __name__ == '__main__':
    main()
