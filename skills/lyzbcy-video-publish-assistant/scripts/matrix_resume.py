"""Compact read-only resumption queue; never opens tabs or publishes."""
import argparse, json
from pathlib import Path


def pending(matrix):
    output = []
    for episode in matrix['episodes']:
        for platform, row in episode['platforms'].items():
            status = row.get('status', 'unknown')
            published_states = ('published', 'public', 'published_management_verified', 'published_profile_verified', 'published_article_with_external_video_links')
            if status in published_states and row.get('native_id'):
                if any('under_review' in str(row.get(k, '')) or 'submitted' in str(row.get(k, '')) for k in ('activity_update_status', 'collection_status', 'metadata_update_status')):
                    output.append({'episode': episode['episode'], 'platform': platform, 'status': status, 'next': 'metadata_query_only_never_reupload'})
                continue
            next_step = 'query_only' if row.get('submission_attempted') or row.get('native_id') or status in published_states or 'under_review' in status else 'inspect_existing_object'
            if status in ('awaiting_admin_scan', 'awaiting_admin_verification', 'reopening_admin_verification', 'saved_draft_ready_publish_requires_admin_verification'):
                next_step = 'human_verification_or_current_publication_readback'
            if status == 'published_user_confirmed':
                next_step = 'readback_only_never_resubmit'
            output.append({'episode': episode['episode'], 'platform': platform, 'status': status, 'next': next_step})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('matrix')
    args = parser.parse_args()
    print(json.dumps({'pending': pending(json.loads(Path(args.matrix).read_text(encoding='utf-8')))}, ensure_ascii=False))
