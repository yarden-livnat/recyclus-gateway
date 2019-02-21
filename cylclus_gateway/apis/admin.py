from flask import jsonify
from flask_restplus import Resource, Namespace
from flask_jwt_extended import ( get_jwt_identity, get_raw_jwt,
                jwt_required, fresh_jwt_required, jwt_refresh_token_required)
from webargs.flaskparser import use_args, use_kwargs

from cyclus_gateway.security import User, UserSchema, TokenSchema, auth


api = Namespace('', description='authentication')


@api.route('/register')
class Register(Resource):
    @use_kwargs(UserSchema())
    def post(self, username, password, email, **kwargs):
        if User.query.filter_by(email=email).first():
            return {'message': f'User {email} already exists'}, 401

        user = User(username, email, password, **kwargs).save()
        access_token = auth.get_access_token(user)
        refresh_token = auth.get_refresh_token(user)
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }

@api.route('/unregister')
class unregister(Resource):
    @fresh_jwt_required
    def delete(self):
        identity = get_jwt_identity()
        user = User.query.filter_by(email=identity).first()
        if user:
            auth.revoke_all(identity)
            user.delete()
            return {'message': 'unregistered'}
        else:
            return {'message': 'failed'}, 401


@api.route('/login')
class Login(Resource):
    @use_kwargs(UserSchema(only=('email', 'password')))
    def post(self, email, password):
        user = User.query.filter_by(email=email).first()
        if not user or not user.verify_password(password):
            return {'message': 'Bad username or password'}, 401

        access_token = auth.get_access_token(user, fresh=True)
        refresh_token = auth.get_refresh_token(user)
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }


@api.route('/logout')
class Logout(Resource):
    @jwt_required
    def post(self):
        jti = get_raw_jwt()['jti']
        auth.revoke_token(jti=jti)
        return {'msg' : 'logout'}


@api.route('/token')
class Tokens(Resource):
    @jwt_required
    def get(self):
        identity = get_jwt_identity()
        all_tokens = auth.get_user_active_tokens(identity)
        return TokenSchema(many=True).dump(all_tokens)


@api.route('/token/refresh')
class Refresh(Resource):
    @jwt_refresh_token_required
    def post(self):
        current_user = get_jwt_identity()
        token = auth.get_access_token(current_user)
        return {'access_token': token}, 201


@api.route('/token/revoke/<token_id>')
class Revoke(Resource):
    @jwt_required
    def put(self, token_id):
        identity = get_jwt_identity()
        auth.revoke_token(id=token_id, user_identity=identity)
        return {'message': 'revoked'}