import json, os, shutil, subprocess, tempfile, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import BugReport, Project, PatchReview, VerificationReport
from .projects import UPLOAD_DIR
from .verification import report_to_dict
router = APIRouter(tags=['Workflow'])
class Selection(BaseModel):
    project_id: int

def project_root(db, project_id):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, 'Project not found')
    root = Path(project.extracted_path).resolve()
    if not root.is_relative_to(UPLOAD_DIR.resolve()) or not root.is_dir():
        raise HTTPException(409, 'Project files unavailable; upload again')
    return root

@router.post('/bugs/{bug_id}/investigate')
def investigate(bug_id: int, selection: Selection, db: Session = Depends(get_db)):
    bug = db.get(BugReport, bug_id)
    if not bug: raise HTTPException(404, 'Bug not found')
    root = project_root(db, selection.project_id)
    try:
        from agent.workflow import run_fixproof_workflow
        result = run_fixproof_workflow(bug.title+'\n'+bug.description, str(root))
    except Exception as exc:
            import traceback
            traceback.print_exc()
            raise HTTPException(502, 'Investigation failed. Check Gemini configuration, dependencies and server logs.') from exc
    changes = result['proposed_fix'].get('proposed_changes', [])
    patch_id = None
    if changes:
        patch = PatchReview(bug_id=bug.id, original_code=json.dumps({'project_id':selection.project_id}), proposed_code='\n'.join(c['unified_diff'].rstrip() for c in changes)+'\n', explanation=json.dumps({'investigation':result['investigation'], 'classification':result['classification'], 'issue_classification':result['issue_classification']}, default=str), status='Pending Review')
        db.add(patch); db.flush(); patch_id=patch.id
    bug.status = 'Patch Pending Review' if changes else 'No Safe Patch'
    db.commit()
    return {'patch_id':patch_id,'status':bug.status,'investigation':result['investigation'],'classification':result['classification'],'issue_classification':result['issue_classification']}

@router.post('/patches/{patch_id}/apply-and-verify')
def verify(patch_id: int, db: Session = Depends(get_db)):
    patch = db.get(PatchReview, patch_id)
    if not patch: raise HTTPException(404,'Patch not found')
    if patch.status != 'Approved': raise HTTPException(409,'Approve patch first')
    try: project_id = json.loads(patch.original_code)['project_id']
    except (ValueError, KeyError, TypeError): raise HTTPException(409,'Legacy patch: investigate again to associate a project')
    root = project_root(db, project_id)
    if not shutil.which('docker') or not shutil.which('git'): raise HTTPException(503,'Docker and Git are required for safe verification')
    name='fixproof-'+uuid.uuid4().hex
    status='Failed'; output=''; details='Original project unchanged; temporary copy discarded.'
    with tempfile.TemporaryDirectory() as temp:
        work=Path(temp)/'project'; shutil.copytree(root,work,ignore=shutil.ignore_patterns('.git','.env','.venv','venv','node_modules'))
        try:
            patch_text = patch.proposed_code.rstrip("\r\n") + "\n"

            for args in [
                ['git', 'apply', '-p0', '--recount', '--check', '-'],
                ['git', 'apply', '-p0', '--recount', '-']
            ]:
                              run = subprocess.run(
                    args,
                    cwd=work,
                    input=patch_text.encode("utf-8"),
                    capture_output=True
                )

            if run.returncode:
                    raise ValueError(
                        'Patch rejected: ' +
                        run.stderr.decode("utf-8", errors="replace")
                    )
            run=subprocess.run(['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','1','--pids-limit','128','--user','65534:65534','--tmpfs','/tmp:rw,size=128m','-e','PYTHONDONTWRITEBYTECODE=1','-v',str(work)+':/project:ro','-w','/project','fixproof-verifier','python','-m','pytest','-p','no:cacheprovider','-q'],capture_output=True,text=True,timeout=90)
            output=run.stdout+'\n'+run.stderr
            if run.returncode==0: status='Passed'
            elif run.returncode in (125,126,127): raise HTTPException(503,'Docker verifier unavailable. Build the verifier image first.')
        except ValueError as exc: output=str(exc)
        except subprocess.TimeoutExpired: output='Verification timed out.'
        finally:
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
    report=VerificationReport(bug_id=patch.bug_id,patch_id=patch.id,status=status,test_results=output[-20000:],verification_details=details)
    db.add(report); db.get(BugReport,patch.bug_id).status='Verified' if status=='Passed' else 'Verification Failed'; db.commit(); db.refresh(report)
    return report_to_dict(report)
